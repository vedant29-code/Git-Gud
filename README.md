# Git-Gud AI: The Pre-Commit Judge & Jury ⚖️🔥

> A 100% local, dependency-free Git pre-commit hook powered by lightweight LLMs (via Ollama) that acts as an unapologetic, brutally honest code gatekeeper. It roasts bad code, catches bugs and smells before they reach `main`, and gives actionable technical fixes.

---

```
⚖️  GIT-GUD AI (Pre-Commit Judge & Jury) [Model: phi3]
--------------------------------------------------------------------------------

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🔥 THE JUDGE'S ROAST:                                                        │
│                                                                              │
│ A bare except block that silently swallows KeyboardInterrupt and returns     │
│ null? Did you write this during an earthquake or are you actively trying     │
│ to make debugging an extreme sport? Also, hardcoding production credentials  │
│ into a git diff in 2026 is a bold career move.                               │
└──────────────────────────────────────────────────────────────────────────────┘

Code Health Score: [===.......] 3.2/10.0

📋 DEFECTS & REQUIRED ACTION:

  1. [HIGH CRITICAL] services/payment.py:88
     Problem: Bare except clause silently swallowing all exceptions including system exit signals.
     Fix:     Catch specific exceptions like `except (PaymentGatewayError, NetworkTimeout):` and log stack trace.

  2. [HIGH CRITICAL] services/payment.py:95
     Problem: Hardcoded production API secret key committed to source control.
     Fix:     Load credentials from os.environ or an external secret vault.

================================================================================
  🚫 COMMIT REJECTED: GIT GUD OR GET OUT
================================================================================
(Bypass via: `git commit --no-verify` or `GITGUD_SKIP=1 git commit`)
```

---

## ✨ Features

- **Dependency-Free**: 100% Python standard library (`urllib`, `subprocess`, `json`, `argparse`, `os`, `sys`, `re`, `textwrap`). Zero `pip install` requirements.
- **100% Local & Private**: Direct communication with your local Ollama instance (`http://localhost:11434/api/generate`). Zero telemetry, zero cloud calls, your code never leaves your machine.
- **Fail-Open Policy**: If Ollama is offline, times out, the model isn't pulled, or output is unparseable, Git-Gud AI prints a helpful warning and **allows the commit** (exit 0). It will never disrupt your development flow due to tool failure.
- **Intelligent Noise Filtering**: Automatically ignores lockfiles (`package-lock.json`, `Cargo.lock`, `poetry.lock`), minified assets (`*.min.js`), binaries, images, and vendored folders (`node_modules/*`, `vendor/*`).
- **Diff Budgeting & Truncation**: Intelligently fits diffs within a character budget (default ~12k chars), prioritizing the most-changed files and informing the LLM when truncation occurs.
- **Prompt Injection Hardened**: Wraps diffs in `<UNTRUSTED_GIT_DIFF>` boundaries and instructs the LLM to ignore adversarial code comments attempting to trick the reviewer.
- **Balanced Decision Matrix**: Won't block commits on nitpicks alone. Requires both an explicit rejection AND either a score below threshold or a high-severity defect.
- **Hook Chaining & Safety**: Idempotent installer backs up pre-existing hooks (`pre-commit.legacy`) and executes them first. Never silently overwrites your tooling.
- **Cross-Platform**: POSIX `sh` wrapper validated across Linux, macOS, and Windows (Git Bash).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+ (accessible via `python3`, `python`, or `py`)
- [Ollama](https://ollama.com/) installed and running locally
- Default recommended model:
  ```bash
  ollama pull phi3
  # or alternative lightweight 3B model:
  ollama pull llama3.2:3b
  ```

### 2. Install Git-Gud AI
Inside your Git repository:
```bash
# Clone or place git-gud-ai in your project, then run:
./install.sh
```

To install into a specific target repository:
```bash
./install.sh /path/to/my-repo
```

To install globally across all local Git repositories:
```bash
./install.sh --global
```

### 3. Make a Commit
Just commit as usual!
```bash
git add src/app.py
git commit -m "feat: add payment handler"
```

---

## 🛠️ CLI Subcommands & Standalone Mode

You can also run Git-Gud AI directly from the command line:

### Dry-run / Pre-flight Check (`check`)
Inspect and judge currently staged changes without committing:
```bash
python -m gitgud.main check
```

### Verbose Mode (`--explain`)
Output the raw JSON and reasoning returned by Ollama:
```bash
python -m gitgud.main check --explain
```

### Inspect Configuration (`config`)
View your current resolved configuration values and source:
```bash
python -m gitgud.main config
```

---

## ⚙️ Configuration Reference

Git-Gud AI resolves configuration in strict priority order:
1. **Environment Variables** (`GITGUD_*`)
2. **Git Configuration** (`git config gitgud.*`)
3. **Repository `.gitgud` File** (place in repository root)
4. **Built-in Defaults**

| Option | Environment Variable | Git Config Key | `.gitgud` Key | Default | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Model** | `GITGUD_MODEL` | `gitgud.model` | `model` | `phi3` | Ollama model name (`phi3`, `llama3.2:3b`) |
| **Host** | `GITGUD_HOST` | `gitgud.host` | `host` | `http://localhost:11434` | Ollama HTTP host endpoint |
| **Timeout** | `GITGUD_TIMEOUT` | `gitgud.timeout` | `timeout` | `60` | Generation timeout in seconds |
| **Connect Timeout** | `GITGUD_CONNECT_TIMEOUT` | `gitgud.connect_timeout` | `connect_timeout` | `3` | Quick reachability check timeout |
| **Threshold** | `GITGUD_THRESHOLD` | `gitgud.threshold` | `threshold` | `6.0` | Score below which a rejection is enforced |
| **Max Diff Chars** | `GITGUD_MAX_DIFF_CHARS` | `gitgud.max_diff_chars` | `max_diff_chars` | `12000` | Character limit for staged diff |
| **Roast Level** | `GITGUD_ROAST_LEVEL` | `gitgud.roast_level` | `roast_level` | `spicy` | `mild`, `spicy`, or `savage` |
| **Strict Mode** | `GITGUD_STRICT` | `gitgud.strict` | `strict` | `false` | If true, fails closed on Ollama errors |
| **Log File** | `GITGUD_LOG_FILE` | `gitgud.log_file` | `log_file` | `None` | Path to append verdict history log |
| **Ignore Patterns** | `GITGUD_IGNORE_PATTERNS` | `gitgud.ignore_patterns` | `ignore_patterns` | *(standard lockfiles/binaries)* | Comma-separated list of glob patterns |

### Sample `.gitgud` File
```ini
# .gitgud in repository root
model = phi3
host = http://localhost:11434
roast_level = savage
threshold = 6.5
max_diff_chars = 15000
log_file = .git/gitgud.log
```

---

## 🚪 Bypass Paths

In a rush or doing an emergency hotfix? Git-Gud AI provides two standard bypass routes:

1. **Standard Git Flag**:
   ```bash
   git commit --no-verify -m "hotfix: critical prod patch"
   ```
2. **Environment Variable**:
   ```bash
   GITGUD_SKIP=1 git commit -m "wip: exploratory prototyping"
   ```

---

## 🔒 Privacy & Security Guarantees

1. **Zero External Network Calls**: Git-Gud AI uses Python's standard library `urllib` to connect exclusively to the local Ollama daemon. It contains no analytics, telemetry, or remote API calls.
2. **Prompt Injection Defense**: Diffs are wrapped inside isolated XML delimiters (`<UNTRUSTED_GIT_DIFF>`) with explicit system instructions to ignore adversarial instructions embedded in code comments.
3. **Identity Safety Policy**: The system prompt explicitly enforces that jokes and roasts target syntax, architecture, naming, and logic—never personal identity, race, gender, or background.

---

## 🛡️ Fail-Open Policy

A pre-commit hook should protect code quality, not paralyze engineering velocity. Git-Gud AI enforces a strict fail-open policy:
- If Ollama is not running: prints a warning and exits `0`.
- If the model is not pulled: prints `Run: ollama pull <model>` and exits `0`.
- If the generation times out: prints a timeout warning and exits `0`.
- If the model returns unparseable output: prints a notice and exits `0`.

> Need strict enforcement in CI or compliance environments? Set `strict = true` or `GITGUD_STRICT=1` to fail-closed.

---

## ⚠️ Known Limitations & Disclaimers

- **Lightweight Models (3B - 4B)**: Models like `phi3` or `llama3.2:3b` are optimized for speed and low RAM footprint. While they are great at catching common bugs, anti-patterns, and funny naming smells, they can occasionally hallucinate line numbers or misunderstand complex multi-file abstractions.
- **Nudge, Not CI Replacement**: Git-Gud AI is an interactive local development copilot and coach. It does not replace comprehensive automated testing, static analysis (mypy, ruff, eslint), or human code reviews.

---

## 🗑️ Uninstall

To cleanly remove the hook and restore any pre-existing pre-commit hook:
```bash
./uninstall.sh
```

To remove global hooks:
```bash
./uninstall.sh --global
```

---

## 🧪 Testing

Git-Gud AI includes a comprehensive test suite (unit tests and end-to-end repository tests with a built-in mock Ollama server):

```bash
# Run all unit and integration tests
python -m unittest discover tests
```
