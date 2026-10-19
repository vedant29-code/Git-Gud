"""Interactive Demonstration of Git-Gud AI (The Pre-Commit Judge & Jury).

Demonstrates:
1. Rejection of dangerous & sloppy code with live roast & actionable fixes.
2. Approval of clean, well-structured code.
3. Hook bypass via GITGUD_SKIP=1 or --no-verify.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

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


def print_banner(text: str):
    print("\n" + "=" * 80)
    print(f"  >>> {text}")
    print("=" * 80 + "\n")


def run_demo():
    # Detect available model from Ollama, default to gemma3:4b if available, else phi3
    model = "phi3"
    try:
        import urllib.request, json
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            available = [m.get("name", "") for m in data.get("models", [])]
            for m in available:
                if "gemma3" in m:
                    model = m
                    break
                elif "phi3" in m:
                    model = m
                    break
                elif "llama3" in m:
                    model = m
                    break
    except Exception:
        pass

    project_dir = os.path.dirname(os.path.abspath(__file__))
    demo_dir = tempfile.mkdtemp(prefix="gitgud_live_demo_")

    try:
        print_banner(f"DEMO 1: The Harsh Rejection (Using model '{model}')")
        print("Creating a temporary repository with pre-commit hook installed...")

        subprocess.run(["git", "init", demo_dir], check=True, capture_output=True)
        subprocess.run(["git", "-C", demo_dir, "config", "user.name", "Demo Dev"], check=True)
        subprocess.run(["git", "-C", demo_dir, "config", "user.email", "dev@example.com"], check=True)

        # Configure .gitgud
        with open(os.path.join(demo_dir, ".gitgud"), "w", encoding="utf-8") as f:
            f.write(
                f"model = {model}\n"
                f"timeout = 90\n"
                f"roast_level = spicy\n"
                f"threshold = 6.0\n"
            )

        # Install hook
        hooks_dir = os.path.join(demo_dir, ".git", "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        shutil.copytree(os.path.join(project_dir, "gitgud"), os.path.join(hooks_dir, "gitgud"))
        shutil.copy(os.path.join(project_dir, "hooks", "pre-commit"), os.path.join(hooks_dir, "pre-commit"))

        # Create intentionally terrible code
        bad_code = '''"""Payment processing service."""
import os

AWS_SECRET_KEY = "AKIA_FAKE_SECRET_KEY_EXPOSED_IN_GIT"

def process_payment(user_input):
    # DANGEROUS: Arbitrary code execution
    result = eval(user_input)

    try:
        query = f"SELECT * FROM users WHERE token = '{user_input}'"
        # pretend query execution
    except:
        # Bare except swallowing everything
        pass

    return result
'''
        with open(os.path.join(demo_dir, "payment.py"), "w", encoding="utf-8") as f:
            f.write(bad_code)

        print("Staging 'payment.py' with hardcoded secrets, eval(), and bare except...")
        subprocess.run(["git", "-C", demo_dir, "add", "payment.py"], check=True)

        print("\nAttempting commit: git commit -m 'feat: add payment processing'")
        proc = subprocess.run(
            ["git", "-C", demo_dir, "commit", "-m", "feat: add payment processing"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.stderr:
            print(proc.stderr)
        if proc.stdout:
            print(proc.stdout)

        print(f"Resulting Commit Exit Code: {proc.returncode} (1 = Commit Blocked by Git-Gud AI)")

        time.sleep(1)

        print_banner(f"DEMO 2: The Approval (Using model '{model}')")
        clean_code = '''"""Secure user authentication utilities."""
import os
from typing import Optional

def get_session_timeout() -> int:
    """Retrieve session timeout from environment with safe fallback."""
    raw = os.environ.get("SESSION_TIMEOUT_SECONDS", "3600")
    try:
        return max(60, int(raw))
    except (ValueError, TypeError):
        return 3600
'''
        with open(os.path.join(demo_dir, "auth.py"), "w", encoding="utf-8") as f:
            f.write(clean_code)

        # Unstage bad code, stage only clean code
        subprocess.run(["git", "-C", demo_dir, "reset"], check=True, capture_output=True)
        subprocess.run(["git", "-C", demo_dir, "add", "auth.py"], check=True)

        print("Staged clean 'auth.py' with type annotations and safe error handling.")
        print("Attempting commit: git commit -m 'feat: add session timeout utility'\n")

        proc2 = subprocess.run(
            ["git", "-C", demo_dir, "commit", "-m", "feat: add session timeout utility"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc2.stderr:
            print(proc2.stderr)
        if proc2.stdout:
            print(proc2.stdout)

        print(f"Resulting Commit Exit Code: {proc2.returncode} (0 = Commit Approved & Created)")

    finally:
        shutil.rmtree(demo_dir, ignore_errors=True)
        print_banner("Demo Complete!")


if __name__ == "__main__":
    run_demo()
