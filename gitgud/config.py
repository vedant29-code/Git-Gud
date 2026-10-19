"""Configuration loader for Git-Gud AI.

Resolves settings in strict priority order:
1. Environment variables (e.g. GITGUD_MODEL)
2. Git configuration (e.g. git config gitgud.model)
3. Repository .gitgud config file
4. Built-in defaults
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


DEFAULT_IGNORE_PATTERNS: List[str] = [
    # Lockfiles
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "go.sum",
    "composer.lock",
    "Gemfile.lock",
    # Minified / Compiled / Source maps
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.bundle.js",
    # Binaries & Media
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.webp",
    "*.svg",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.rar",
    "*.7z",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.pyc",
    "*.pyo",
    "*.class",
    # Generated / Vendored directories
    "node_modules/*",
    "vendor/*",
    "dist/*",
    "build/*",
    ".venv/*",
    "venv/*",
    ".tox/*",
    "__pycache__/*",
    ".git/*",
]


@dataclass
class GitGudConfig:
    """Resolved configuration values for Git-Gud AI."""
    model: str = "phi3"
    host: str = "http://localhost:11434"
    timeout: float = 60.0
    connect_timeout: float = 3.0
    threshold: float = 6.0
    max_diff_chars: int = 12000
    roast_level: str = "spicy"
    strict: bool = False
    ignore_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    log_file: Optional[str] = None


def _to_bool(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    clean = str(val).strip().lower()
    if clean in ("1", "true", "yes", "on", "enable", "enabled"):
        return True
    if clean in ("0", "false", "no", "off", "disable", "disabled"):
        return False
    return default


def _to_float(val: Optional[str], default: float) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _to_int(val: Optional[str], default: int) -> int:
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _parse_patterns(val: Optional[str]) -> Optional[List[str]]:
    if not val:
        return None
    patterns: List[str] = []
    # Can be separated by commas or newlines
    for line in val.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        for item in line.split(","):
            cleaned = item.strip()
            if cleaned and not cleaned.startswith("#"):
                patterns.append(cleaned)
    return patterns if patterns else None


def _get_git_config(key: str, repo_root: Optional[str] = None) -> Optional[str]:
    """Retrieve a git config value via `git config --get`."""
    try:
        cmd = ["git", "config", "--get", f"gitgud.{key}"]
        res = subprocess.run(
            cmd,
            cwd=repo_root or os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=False,
        )
        if res.returncode == 0:
            val = res.stdout.strip()
            return val if val else None
    except Exception:
        pass
    return None


def _find_repo_root() -> Optional[str]:
    """Find git repository root directory."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=False,
        )
        if res.returncode == 0:
            path = res.stdout.strip()
            if path and os.path.isdir(path):
                return path
    except Exception:
        pass
    return None


def _load_gitgud_file(repo_root: Optional[str]) -> dict:
    """Parse .gitgud config file in the repository root if present."""
    if not repo_root:
        return {}

    config_path = os.path.join(repo_root, ".gitgud")
    if not os.path.isfile(config_path):
        return {}

    data: dict = {}
    try:
        with open(config_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                elif ":" in line:
                    k, v = line.split(":", 1)
                else:
                    continue

                k = k.strip().lower().replace("-", "_")
                v = v.strip().strip("'\"")
                data[k] = v
    except Exception:
        pass
    return data


def load_config(repo_root: Optional[str] = None) -> GitGudConfig:
    """Load configuration respecting precedence:
    Environment > Git Config > .gitgud file > Defaults.
    """
    if repo_root is None:
        repo_root = _find_repo_root()

    file_cfg = _load_gitgud_file(repo_root)

    def resolve(key: str, env_name: str, default: str) -> str:
        # 1. Environment variable
        env_val = os.environ.get(env_name)
        if env_val is not None and env_val.strip() != "":
            return env_val.strip()

        # 2. Git config
        git_val = _get_git_config(key, repo_root)
        if git_val is not None and git_val.strip() != "":
            return git_val.strip()

        # 3. .gitgud file
        if key in file_cfg and file_cfg[key]:
            return file_cfg[key]

        # 4. Default
        return default

    # Model
    model = resolve("model", "GITGUD_MODEL", "phi3")

    # Host
    host = resolve("host", "GITGUD_HOST", "http://localhost:11434").rstrip("/")

    # Timeout
    timeout_raw = resolve("timeout", "GITGUD_TIMEOUT", "60")
    timeout = _to_float(timeout_raw, 60.0)

    # Connect timeout
    connect_timeout_raw = resolve("connect_timeout", "GITGUD_CONNECT_TIMEOUT", "3")
    connect_timeout = _to_float(connect_timeout_raw, 3.0)

    # Threshold
    threshold_raw = resolve("threshold", "GITGUD_THRESHOLD", "6.0")
    threshold = _to_float(threshold_raw, 6.0)

    # Max diff chars
    max_diff_raw = resolve("max_diff_chars", "GITGUD_MAX_DIFF_CHARS", "12000")
    max_diff_chars = _to_int(max_diff_raw, 12000)

    # Roast level
    roast_level_raw = resolve("roast_level", "GITGUD_ROAST_LEVEL", "spicy").lower()
    if roast_level_raw not in ("mild", "spicy", "savage"):
        roast_level_raw = "spicy"
    roast_level = roast_level_raw

    # Strict mode
    strict_raw = resolve("strict", "GITGUD_STRICT", "false")
    strict = _to_bool(strict_raw, False)

    # Ignore patterns
    env_ignore = os.environ.get("GITGUD_IGNORE_PATTERNS")
    git_ignore = _get_git_config("ignore_patterns", repo_root)
    file_ignore = file_cfg.get("ignore_patterns") or file_cfg.get("ignore")

    raw_ignore = env_ignore or git_ignore or file_ignore
    parsed_patterns = _parse_patterns(raw_ignore)
    if parsed_patterns is not None:
        ignore_patterns = parsed_patterns
    else:
        ignore_patterns = list(DEFAULT_IGNORE_PATTERNS)

    # Log file
    log_file_raw = resolve("log_file", "GITGUD_LOG_FILE", "")
    log_file = log_file_raw if log_file_raw else None

    return GitGudConfig(
        model=model,
        host=host,
        timeout=timeout,
        connect_timeout=connect_timeout,
        threshold=threshold,
        max_diff_chars=max_diff_chars,
        roast_level=roast_level,
        strict=strict,
        ignore_patterns=ignore_patterns,
        log_file=log_file,
    )
