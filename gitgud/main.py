import argparse
import datetime
import os
import sys

# Ensure parent package directory is always on sys.path regardless of how main.py is invoked
_PKG_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)

# Reconfigure stdout and stderr to utf-8 safely
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import Optional

from gitgud import __version__
from gitgud.config import GitGudConfig, load_config
from gitgud.diff import DiffResult, get_staged_diff
from gitgud.judge import JudgeResult, judge_diff
from gitgud.render import Spinner, render_report, safe_print


def log_verdict(log_path: Optional[str], result: JudgeResult, diff_res: DiffResult, model: str):
    """Optionally append record to verdict log file."""
    if not log_path:
        return
    try:
        now = datetime.datetime.now().isoformat()
        entry = (
            f"[{now}] model={model} verdict={result.verdict} score={result.score:.1f} "
            f"files={diff_res.included_files}/{diff_res.total_files} "
            f"fail_open={result.is_fail_open} "
            f"roast={repr(result.roast[:80])}\n"
        )
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def execute_judge_pipeline(
    config: GitGudConfig,
    explain: bool = False,
    is_dry_run: bool = False,
) -> int:
    """Executes the pre-commit diff collection, judging, rendering, and returns exit code."""
    # 1. Collect staged diff
    diff_res = get_staged_diff(
        ignore_patterns=config.ignore_patterns,
        max_diff_chars=config.max_diff_chars,
    )

    # 2. Check early skip conditions
    if diff_res.skip_reason:
        # If dry-run and diff is empty, notify user
        if is_dry_run:
            print(f"[git-gud dry-run]: {diff_res.skip_reason}")
        return 0

    # 3. Perform LLM Judge with Spinner
    spinner_msg = f"Git-Gud AI is judging staged changes with '{config.model}'..."
    with Spinner(spinner_msg):
        judge_res = judge_diff(diff_res.diff_text, config)

    # 4. Render terminal report
    report_output = render_report(judge_res, config.model)
    safe_print(report_output)

    # 5. Explain mode (print raw response)
    if explain and judge_res.raw_response:
        print("\n--- [GIT-GUD EXPLAIN: RAW MODEL OUTPUT] ---")
        print(judge_res.raw_response)
        print("-------------------------------------------\n")

    # 6. Log verdict if configured
    log_verdict(config.log_file, judge_res, diff_res, config.model)

    # 7. Determine exit code
    if judge_res.verdict.lower() == "reject":
        return 1

    # If fail-open error occurred and strict mode is active:
    if judge_res.is_fail_open and config.strict:
        print("[git-gud error]: Commit blocked by strict mode due to judge failure.", file=sys.stderr)
        return 1

    return 0


def cmd_config(config: GitGudConfig):
    """Print the resolved configuration."""
    print("=== Git-Gud AI Resolved Configuration ===")
    print(f"  model:           {config.model}")
    print(f"  host:            {config.host}")
    print(f"  timeout:         {config.timeout}s")
    print(f"  connect_timeout: {config.connect_timeout}s")
    print(f"  threshold:       {config.threshold}/10.0")
    print(f"  max_diff_chars:  {config.max_diff_chars}")
    print(f"  roast_level:     {config.roast_level}")
    print(f"  strict:          {config.strict}")
    print(f"  log_file:        {config.log_file or '(disabled)'}")
    print(f"  ignore_patterns: ({len(config.ignore_patterns)} patterns configured)")
    for pat in config.ignore_patterns[:5]:
        print(f"    - {pat}")
    if len(config.ignore_patterns) > 5:
        print(f"    ... and {len(config.ignore_patterns) - 5} more")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gitgud",
        description="Git-Gud AI: The Pre-Commit Judge & Jury.",
    )
    parser.add_argument("--version", action="version", version=f"git-gud {__version__}")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run code judgment without committing (same as 'check' subcommand)",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print verbose LLM response and prompt metadata",
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    # 'run' subcommand
    subparsers.add_parser("run", help="Run pre-commit check on staged diff (default)")

    # 'check' subcommand
    check_parser = subparsers.add_parser("check", help="Dry-run judgment on staged changes")
    check_parser.add_argument("--explain", action="store_true", help="Print verbose LLM response")

    # 'config' subcommand
    subparsers.add_parser("config", help="Display resolved Git-Gud configuration")

    args = parser.parse_args()

    config = load_config()

    if args.subcommand == "config":
        cmd_config(config)
        return 0

    is_dry_run = args.dry_run or (args.subcommand == "check")
    explain = args.explain or (hasattr(args, "explain") and getattr(args, "explain"))

    try:
        return execute_judge_pipeline(config, explain=explain, is_dry_run=is_dry_run)
    except KeyboardInterrupt:
        print("\n[git-gud]: Interrupted by user. Allowing commit.", file=sys.stderr)
        return 0
    except Exception as e:
        # Ultimate fail-open catch-all
        if config.strict:
            print(f"[git-gud fatal]: {e}", file=sys.stderr)
            return 1
        print(f"[git-gud warning]: Unexpected error ({e}). Allowing commit (fail-open).", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
