"""Diff collection, filtering, truncation, and normalization for Git-Gud AI."""

import fnmatch
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class FileDiff:
    """Represents the diff for a single file."""
    path: str
    content: str
    added_lines: int
    deleted_lines: int
    is_binary: bool

    @property
    def total_changes(self) -> int:
        return self.added_lines + self.deleted_lines

    @property
    def char_count(self) -> int:
        return len(self.content)


@dataclass
class DiffResult:
    """Result of diff collection."""
    diff_text: str
    total_files: int
    included_files: int
    ignored_files: int
    is_truncated: bool
    skip_reason: Optional[str] = None


def get_git_info(cwd: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Return (repo_toplevel, git_dir) or (None, None) if not in a git repo."""
    try:
        res_top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
        if res_top.returncode != 0:
            return None, None
        top = res_top.stdout.strip()

        res_git = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
        if res_git.returncode != 0:
            return top, None
        git_dir = res_git.stdout.strip()
        if not os.path.isabs(git_dir) and top:
            git_dir = os.path.normpath(os.path.join(top, git_dir))
        return top, git_dir
    except Exception:
        return None, None


def is_merge_or_rebase(git_dir: Optional[str]) -> bool:
    """Check if repository is in the middle of a merge or rebase."""
    if not git_dir or not os.path.isdir(git_dir):
        return False

    markers = [
        "MERGE_HEAD",
        "rebase-merge",
        "rebase-apply",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
    ]
    for marker in markers:
        if os.path.exists(os.path.join(git_dir, marker)):
            return True
    return False


def matches_any_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if relative file path matches any glob pattern."""
    norm_path = file_path.replace("\\", "/")
    filename = os.path.basename(norm_path)

    for pattern in patterns:
        pat = pattern.replace("\\", "/").strip()
        if not pat:
            continue
        # Direct glob match on full path
        if fnmatch.fnmatch(norm_path, pat):
            return True
        # Match on filename alone
        if fnmatch.fnmatch(filename, pat):
            return True
        # Directory prefix match (e.g. "vendor/*" or "node_modules/")
        if pat.endswith("/*"):
            prefix = pat[:-2].rstrip("/") + "/"
            if norm_path.startswith(prefix) or f"/{prefix}" in f"/{norm_path}":
                return True
        elif pat.endswith("/"):
            prefix = pat.rstrip("/") + "/"
            if norm_path.startswith(prefix) or f"/{prefix}" in f"/{norm_path}":
                return True
    return False


def _parse_diff_blocks(raw_diff: str) -> List[FileDiff]:
    """Split raw git diff into structured FileDiff blocks."""
    # Diffs start with `diff --git a/... b/...`
    # Normalize line endings to \n
    raw_diff = raw_diff.replace("\r\n", "\n").replace("\r", "\n")

    pattern = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.MULTILINE)
    matches = list(pattern.finditer(raw_diff))

    if not matches:
        # Check if single file diff without standard header
        if raw_diff.strip():
            return [
                FileDiff(
                    path="staged_changes",
                    content=raw_diff.strip(),
                    added_lines=sum(1 for l in raw_diff.splitlines() if l.startswith("+")),
                    deleted_lines=sum(1 for l in raw_diff.splitlines() if l.startswith("-")),
                    is_binary=False,
                )
            ]
        return []

    file_diffs: List[FileDiff] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_diff)
        block = raw_diff[start:end].rstrip()

        # Path: prefer b/ path unless /dev/null
        b_path = match.group(2)
        a_path = match.group(1)
        path = b_path if b_path != "/dev/null" else a_path

        is_binary = "Binary files " in block or "GIT binary patch" in block

        added = 0
        deleted = 0
        for line in block.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                deleted += 1

        file_diffs.append(
            FileDiff(
                path=path,
                content=block,
                added_lines=added,
                deleted_lines=deleted,
                is_binary=is_binary,
            )
        )

    return file_diffs


def get_staged_diff(
    ignore_patterns: Optional[List[str]] = None,
    max_diff_chars: int = 12000,
    cwd: Optional[str] = None,
) -> DiffResult:
    """Collect, filter, normalize, and truncate staged git diff.

    Returns a DiffResult. If skip_reason is populated, diff should be bypassed.
    """
    # 1. Environment skip variable
    if os.environ.get("GITGUD_SKIP") in ("1", "true", "yes", "TRUE"):
        return DiffResult(
            diff_text="",
            total_files=0,
            included_files=0,
            ignored_files=0,
            is_truncated=False,
            skip_reason="GITGUD_SKIP environment variable is set",
        )

    # 2. Check repo & merge/rebase state
    top_dir, git_dir = get_git_info(cwd)
    if is_merge_or_rebase(git_dir):
        return DiffResult(
            diff_text="",
            total_files=0,
            included_files=0,
            ignored_files=0,
            is_truncated=False,
            skip_reason="Merge or rebase in progress",
        )

    # 3. Run git diff --cached --unified=3
    # Note: --unified=3 gives standard 3 lines of context
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--unified=3"],
            cwd=top_dir or cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
            return DiffResult(
                diff_text="",
                total_files=0,
                included_files=0,
                ignored_files=0,
                is_truncated=False,
                skip_reason=f"Git diff failed: {err_msg or 'unknown error'}",
            )
        raw_output = proc.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return DiffResult(
            diff_text="",
            total_files=0,
            included_files=0,
            ignored_files=0,
            is_truncated=False,
            skip_reason=f"Subprocess error: {str(e)}",
        )

    # 4. Check if diff is empty
    if not raw_output.strip():
        return DiffResult(
            diff_text="",
            total_files=0,
            included_files=0,
            ignored_files=0,
            is_truncated=False,
            skip_reason="Empty staged diff (nothing staged or no changes)",
        )

    # 5. Parse and filter
    all_blocks = _parse_diff_blocks(raw_output)
    total_files = len(all_blocks)

    if not all_blocks:
        return DiffResult(
            diff_text="",
            total_files=0,
            included_files=0,
            ignored_files=0,
            is_truncated=False,
            skip_reason="No file changes found in diff",
        )

    patterns = ignore_patterns or []
    filtered_blocks: List[FileDiff] = []
    ignored_count = 0

    for block in all_blocks:
        if block.is_binary:
            ignored_count += 1
            continue
        if matches_any_pattern(block.path, patterns):
            ignored_count += 1
            continue
        filtered_blocks.append(block)

    if not filtered_blocks:
        return DiffResult(
            diff_text="",
            total_files=total_files,
            included_files=0,
            ignored_files=ignored_count,
            is_truncated=False,
            skip_reason="All staged files were filtered out by ignore patterns or binary detection",
        )

    # 6. Truncate if character count exceeds budget
    # Sort files by total changes descending (prioritize files with the most lines changed)
    sorted_blocks = sorted(filtered_blocks, key=lambda b: (b.total_changes, b.char_count), reverse=True)

    included_diffs: List[str] = []
    current_chars = 0
    is_truncated = False
    included_count = 0

    # Leave room for truncation disclaimer
    effective_budget = max(500, max_diff_chars)

    for b in sorted_blocks:
        block_len = len(b.content)
        if current_chars + block_len + 2 <= effective_budget:
            included_diffs.append(b.content)
            current_chars += block_len + 2
            included_count += 1
        else:
            # Check if this is the very first file and it alone exceeds the budget
            if included_count == 0:
                # Truncate this single file's diff
                slice_len = effective_budget - 200
                truncated_content = b.content[:slice_len] + "\n... [Remaining lines of file truncated]"
                included_diffs.append(truncated_content)
                current_chars += len(truncated_content)
                included_count = 1
            is_truncated = True
            break

    if len(sorted_blocks) > included_count:
        is_truncated = True

    combined_diff = "\n\n".join(included_diffs)

    if is_truncated:
        omitted = total_files - included_count
        combined_diff += (
            f"\n\n[NOTE: Staged diff was truncated to ~{effective_budget} characters. "
            f"{omitted} file(s) omitted due to character budget.]"
        )

    return DiffResult(
        diff_text=combined_diff,
        total_files=total_files,
        included_files=included_count,
        ignored_files=ignored_count,
        is_truncated=is_truncated,
        skip_reason=None,
    )
