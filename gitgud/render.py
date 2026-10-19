"""Terminal rendering, ANSI styling, spinner, and report formatting for Git-Gud AI."""

import os
import shutil
import sys
import textwrap
import threading
import time
from typing import List, Optional

from gitgud.judge import Issue, JudgeResult


def supports_color() -> bool:
    """Determine if current terminal environment supports ANSI colors."""
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    # Check if stderr/stdout is a tty
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def safe_print(text: str, file=None):
    """Print text safely, replacing unencodable characters if stream encoding is restricted."""
    target = file or sys.stdout
    try:
        print(text, file=target)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", "ascii") or "ascii"
        fallback = text.encode(encoding, errors="replace").decode(encoding)
        print(fallback, file=target)


class Style:
    """ANSI color codes with automatic NO_COLOR disabling."""
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def _c(self, code: str) -> str:
        return code if self.enabled else ""

    @property
    def RESET(self) -> str:
        return self._c("\033[0m")

    @property
    def BOLD(self) -> str:
        return self._c("\033[1m")

    @property
    def DIM(self) -> str:
        return self._c("\033[2m")

    @property
    def ITALIC(self) -> str:
        return self._c("\033[3m")

    @property
    def RED(self) -> str:
        return self._c("\033[38;5;196m")

    @property
    def BRIGHT_RED(self) -> str:
        return self._c("\033[91m")

    @property
    def GREEN(self) -> str:
        return self._c("\033[38;5;46m")

    @property
    def BRIGHT_GREEN(self) -> str:
        return self._c("\033[92m")

    @property
    def YELLOW(self) -> str:
        return self._c("\033[38;5;220m")

    @property
    def BLUE(self) -> str:
        return self._c("\033[38;5;75m")

    @property
    def MAGENTA(self) -> str:
        return self._c("\033[38;5;201m")

    @property
    def CYAN(self) -> str:
        return self._c("\033[38;5;51m")

    @property
    def GRAY(self) -> str:
        return self._c("\033[38;5;244m")

    @property
    def BG_RED(self) -> str:
        return self._c("\033[48;5;52m")

    @property
    def BG_GREEN(self) -> str:
        return self._c("\033[48;5;22m")


class Spinner:
    """Lightweight animated terminal spinner for long-running operations."""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Git-Gud AI is reviewing your code..."):
        self.message = message
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.is_tty = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
        self.style = Style(supports_color())

    def _spin(self):
        idx = 0
        while not self.stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            msg = f"\r{self.style.CYAN}{frame}{self.style.RESET} {self.style.BOLD}{self.message}{self.style.RESET}"
            sys.stderr.write(msg)
            sys.stderr.flush()
            idx += 1
            time.sleep(0.08)

        # Clear spinner line
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    def __enter__(self):
        if self.is_tty:
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            sys.stderr.write(f"{self.message}\n")
            sys.stderr.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=1.0)


def get_terminal_width(default: int = 80) -> int:
    try:
        width = shutil.get_terminal_size((default, 24)).columns
        return max(40, min(100, width))
    except Exception:
        return default


def render_score_meter(score: float, style: Style) -> str:
    """Format a 10-block visual score bar."""
    clamped = max(0.0, min(10.0, score))
    total_blocks = 10
    filled_blocks = int(round(clamped))
    empty_blocks = total_blocks - filled_blocks

    if clamped >= 7.5:
        color = style.BRIGHT_GREEN
    elif clamped >= 5.0:
        color = style.YELLOW
    else:
        color = style.BRIGHT_RED

    bar = f"[{'=' * filled_blocks}{'.' * empty_blocks}]"
    return f"{color}{bar}{style.RESET} {style.BOLD}{score:.1f}/10.0{style.RESET}"


def render_roast_box(roast: str, width: int, style: Style) -> str:
    """Wrap roast in a distinct framed card."""
    content_width = width - 4
    wrapped_lines = []
    for paragraph in roast.splitlines():
        if paragraph.strip():
            wrapped_lines.extend(textwrap.wrap(paragraph, width=content_width))
        else:
            wrapped_lines.append("")

    top_border = f"{style.MAGENTA}┌{'─' * (width - 2)}┐{style.RESET}"
    bottom_border = f"{style.MAGENTA}└{'─' * (width - 2)}┘{style.RESET}"

    lines = [top_border]
    lines.append(f"{style.MAGENTA}│{style.RESET} {style.BOLD}{style.YELLOW}🔥 THE JUDGE'S ROAST:{style.RESET}{' ' * (width - 23)}{style.MAGENTA}│{style.RESET}")
    lines.append(f"{style.MAGENTA}│{' ' * (width - 2)}│{style.RESET}")

    for line in wrapped_lines:
        padding = content_width - len(line)
        lines.append(f"{style.MAGENTA}│{style.RESET} {style.ITALIC}{line}{style.RESET}{' ' * padding} {style.MAGENTA}│{style.RESET}")

    lines.append(bottom_border)
    return "\n".join(lines)


def render_issues_list(issues: List[Issue], width: int, style: Style) -> str:
    """Render structured issues list with severity tags and fixes."""
    if not issues:
        return f"{style.GREEN}✨ No technical defects detected.{style.RESET}"

    lines = []
    lines.append(f"{style.BOLD}📋 DEFECTS & REQUIRED ACTION:{style.RESET}")

    for idx, issue in enumerate(issues, start=1):
        sev = issue.severity.upper()
        if sev == "HIGH":
            badge = f"{style.BRIGHT_RED}[HIGH CRITICAL]{style.RESET}"
        elif sev == "MED":
            badge = f"{style.YELLOW}[MED SMELL]{style.RESET}"
        else:
            badge = f"{style.BLUE}[LOW NITPICK]{style.RESET}"

        loc = f"{issue.file}:{issue.line}" if issue.line > 0 else issue.file
        lines.append(f"\n  {style.BOLD}{idx}. {badge} {style.CYAN}{loc}{style.RESET}")

        prob_wrap = textwrap.wrap(issue.problem, width=width - 8)
        for p in prob_wrap:
            lines.append(f"     {style.GRAY}Problem:{style.RESET} {p}")

        if issue.fix:
            fix_wrap = textwrap.wrap(issue.fix, width=width - 8)
            for f in fix_wrap:
                lines.append(f"     {style.GREEN}Fix:{style.RESET}     {style.BOLD}{f}{style.RESET}")

    return "\n".join(lines)


def render_verdict_banner(verdict: str, width: int, style: Style) -> str:
    """Render bold banner indicating APPROVAL or REJECTION."""
    is_approve = verdict.lower() == "approve"

    if is_approve:
        text = "⚖️  COMMIT APPROVED: PROCEED WITH CAUTION"
        bar = "=" * width
        return (
            f"\n{style.BRIGHT_GREEN}{style.BOLD}{bar}\n"
            f"  {text}\n"
            f"{bar}{style.RESET}\n"
        )
    else:
        text = "🚫 COMMIT REJECTED: GIT GUD OR GET OUT"
        bar = "=" * width
        bypass = "(Bypass via: `git commit --no-verify` or `GITGUD_SKIP=1 git commit`)"
        return (
            f"\n{style.BRIGHT_RED}{style.BOLD}{bar}\n"
            f"  {text}\n"
            f"{bar}{style.RESET}\n"
            f"{style.GRAY}{bypass}{style.RESET}\n"
        )


def render_report(result: JudgeResult, model_name: str) -> str:
    """Format the full pre-commit judgment report."""
    color_enabled = supports_color()
    style = Style(color_enabled)
    width = get_terminal_width(80)

    output: List[str] = []

    # Header
    header = f"{style.BOLD}⚖️  GIT-GUD AI (Pre-Commit Judge & Jury){style.RESET} {style.GRAY}[Model: {model_name}]{style.RESET}"
    output.append(header)
    output.append(f"{style.GRAY}{'-' * width}{style.RESET}")

    # Warning if fail-open or partial
    if result.warning:
        output.append(f"\n{style.YELLOW}⚠️  [git-gud warning]: {result.warning}{style.RESET}")
        if result.is_fail_open:
            output.append(f"{style.GRAY}(Fail-open policy active: commit allowed despite error.){style.RESET}")

    # Roast card
    if result.roast:
        output.append("\n" + render_roast_box(result.roast, width, style))

    # Score Meter
    output.append(f"\n{style.BOLD}Code Health Score:{style.RESET} {render_score_meter(result.score, style)}")

    # Issues
    if result.issues:
        output.append("\n" + render_issues_list(result.issues, width, style))

    # Final Verdict Banner
    output.append(render_verdict_banner(result.verdict, width, style))

    return "\n".join(output)
