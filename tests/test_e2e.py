"""End-to-End integration tests for Git-Gud AI using a mock Ollama server and real git repos."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from tests.mock_ollama import MockOllamaServer


class TestEndToEnd(unittest.TestCase):
    """Full lifecycle integration tests inside temporary Git repositories."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def create_test_repo(self, mock_host: str, model: str = "phi3", strict: bool = False) -> str:
        """Create an isolated test git repository with Git-Gud AI hook installed."""
        tmp_dir = tempfile.mkdtemp(prefix="gitgud_e2e_")

        # 1. git init
        subprocess.run(["git", "init", tmp_dir], check=True, capture_output=True)
        subprocess.run(["git", "-C", tmp_dir, "config", "user.name", "Judge Tester"], check=True)
        subprocess.run(["git", "-C", tmp_dir, "config", "user.email", "judge@test.local"], check=True)

        # 2. Configure .gitgud
        config_path = os.path.join(tmp_dir, ".gitgud")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(
                f"host = {mock_host}\n"
                f"model = {model}\n"
                f"connect_timeout = 1.0\n"
                f"timeout = 2.0\n"
                f"strict = {'true' if strict else 'false'}\n"
                f"threshold = 6.0\n"
            )

        # 3. Install hooks
        hooks_dir = os.path.join(tmp_dir, ".git", "hooks")
        os.makedirs(hooks_dir, exist_ok=True)

        # Copy gitgud package into hooks dir
        shutil.copytree(
            os.path.join(self.project_root, "gitgud"),
            os.path.join(hooks_dir, "gitgud"),
        )
        # Copy hook script
        shutil.copy(
            os.path.join(self.project_root, "hooks", "pre-commit"),
            os.path.join(hooks_dir, "pre-commit"),
        )

        return tmp_dir

    def test_e2e_approve_commit(self):
        """Clean commit approved by LLM -> commit succeeds."""
        mock_response = json.dumps({
            "verdict": "approve",
            "score": 9.0,
            "roast": "Surprisingly competent code. Proceed.",
            "issues": [],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                test_file = os.path.join(repo, "clean.py")
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write("def add(a: int, b: int) -> int:\n    return a + b\n")

                subprocess.run(["git", "-C", repo, "add", "clean.py"], check=True)
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "-m", "feat: add function"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 0)
                self.assertIn("COMMIT APPROVED", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_reject_commit(self):
        """Sloppy commit rejected by LLM -> commit is blocked (exit code 1)."""
        mock_response = json.dumps({
            "verdict": "reject",
            "score": 2.5,
            "roast": "This code looks like it was written during an earthquake.",
            "issues": [
                {
                    "file": "bad.py",
                    "line": 4,
                    "severity": "high",
                    "problem": "Hardcoded database password and unhandled exception.",
                    "fix": "Use environment variables and handle DatabaseError.",
                }
            ],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                bad_file = os.path.join(repo, "bad.py")
                with open(bad_file, "w", encoding="utf-8") as f:
                    f.write("DB_PASS = 'secret123'\ndef connect():\n    pass\n")

                subprocess.run(["git", "-C", repo, "add", "bad.py"], check=True)
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "-m", "bad commit"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 1)
                self.assertIn("COMMIT REJECTED", res.stderr)
                self.assertIn("Hardcoded database password", res.stderr)
                self.assertIn("Use environment variables", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_server_down_fail_open(self):
        """Server is offline -> fail-open warning printed, commit succeeds."""
        # Port 59876 is closed
        repo = self.create_test_repo("http://127.0.0.1:59876", strict=False)
        try:
            file_path = os.path.join(repo, "work.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("print('server offline test')\n")

            subprocess.run(["git", "-C", repo, "add", "work.py"], check=True)
            res = subprocess.run(
                ["git", "-C", repo, "commit", "-m", "work while offline"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("unreachable", res.stderr)
            self.assertIn("Fail-open policy active", res.stderr)
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_server_timeout_fail_open(self):
        """Ollama takes longer than timeout -> fail-open warning, commit succeeds."""
        # Server delays for 3.0 seconds, while connect_timeout is 1.0s and timeout is 2.0s
        with MockOllamaServer(delay=3.0) as server:
            repo = self.create_test_repo(server.host_url, strict=False)
            try:
                file_path = os.path.join(repo, "slow.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("print('slow test')\n")

                subprocess.run(["git", "-C", repo, "add", "slow.py"], check=True)
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "-m", "commit with slow server"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 0)
                self.assertIn("Fail-open policy active", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_garbage_response_fail_open(self):
        """LLM returns garbage non-JSON -> fail-open warning, commit succeeds."""
        with MockOllamaServer(generate_response="I am an AI and I cannot judge code today!") as server:
            repo = self.create_test_repo(server.host_url, strict=False)
            try:
                file_path = os.path.join(repo, "any.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("print('any')\n")

                subprocess.run(["git", "-C", repo, "add", "any.py"], check=True)
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "-m", "garbage test"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 0)
                self.assertIn("Unparseable LLM response", res.stderr)
                self.assertIn("Fail-open policy active", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_empty_diff_skips(self):
        """Empty commit / no changes -> hook skips immediately."""
        with MockOllamaServer() as server:
            repo = self.create_test_repo(server.host_url)
            try:
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "--allow-empty", "-m", "empty commit"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 0)
                # Ensure no judge report was printed
                self.assertNotIn("GIT-GUD AI (Pre-Commit Judge & Jury)", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_no_verify_bypass(self):
        """git commit --no-verify bypasses pre-commit completely."""
        mock_response = json.dumps({
            "verdict": "reject",
            "score": 1.0,
            "roast": "Terrible.",
            "issues": [{"file": "f.py", "line": 1, "severity": "high", "problem": "p", "fix": "f"}],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                file_path = os.path.join(repo, "bad.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("import broken\n")

                subprocess.run(["git", "-C", repo, "add", "bad.py"], check=True)
                # Commit with --no-verify
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "--no-verify", "-m", "bypassed commit"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 0)
                self.assertNotIn("COMMIT REJECTED", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_gitgud_skip_env_bypass(self):
        """GITGUD_SKIP=1 bypasses pre-commit hook."""
        mock_response = json.dumps({
            "verdict": "reject",
            "score": 1.0,
            "roast": "Terrible.",
            "issues": [{"file": "f.py", "line": 1, "severity": "high", "problem": "p", "fix": "f"}],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                file_path = os.path.join(repo, "bad.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("import broken\n")

                subprocess.run(["git", "-C", repo, "add", "bad.py"], check=True)
                env = os.environ.copy()
                env["GITGUD_SKIP"] = "1"
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "-m", "skip env commit"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                )
                self.assertEqual(res.returncode, 0)
                self.assertNotIn("COMMIT REJECTED", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_legacy_hook_chaining(self):
        """Existing legacy hook is executed before Git-Gud AI."""
        mock_response = json.dumps({
            "verdict": "approve",
            "score": 9.0,
            "roast": "Good.",
            "issues": [],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                # Add a legacy hook that fails
                legacy_path = os.path.join(repo, ".git", "hooks", "pre-commit.legacy")
                with open(legacy_path, "w", encoding="utf-8") as f:
                    f.write("#!/bin/sh\necho 'LEGACY_HOOK_FAILED'\nexit 42\n")

                file_path = os.path.join(repo, "test.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("x = 1\n")

                subprocess.run(["git", "-C", repo, "add", "test.py"], check=True)
                res = subprocess.run(
                    ["git", "-C", repo, "commit", "-m", "chain test"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertNotEqual(res.returncode, 0)
                self.assertIn("LEGACY_HOOK_FAILED", res.stderr)
                # Git-Gud should not even have executed
                self.assertNotIn("GIT-GUD AI", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_subdirectory_commit(self):
        """Commits initiated from nested subdirectories work seamlessly."""
        mock_response = json.dumps({
            "verdict": "approve",
            "score": 9.5,
            "roast": "Perfection.",
            "issues": [],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                sub_dir = os.path.join(repo, "src", "nested", "pkg")
                os.makedirs(sub_dir, exist_ok=True)
                file_path = os.path.join(sub_dir, "feature.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("def feature(): return True\n")

                subprocess.run(["git", "-C", sub_dir, "add", "feature.py"], check=True)
                res = subprocess.run(
                    ["git", "-C", sub_dir, "commit", "-m", "sub commit"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(res.returncode, 0)
                self.assertIn("COMMIT APPROVED", res.stderr)
            finally:
                shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_gitgud_check_cli(self):
        """'gitgud check' standalone CLI command evaluates staged diff without committing."""
        mock_response = json.dumps({
            "verdict": "reject",
            "score": 3.0,
            "roast": "Needs work.",
            "issues": [
                {
                    "file": "check.py",
                    "line": 1,
                    "severity": "high",
                    "problem": "Bad practice",
                    "fix": "Fix it",
                }
            ],
        })
        with MockOllamaServer(generate_response=mock_response) as server:
            repo = self.create_test_repo(server.host_url)
            try:
                file_path = os.path.join(repo, "check.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("bad_code = True\n")

                subprocess.run(["git", "-C", repo, "add", "check.py"], check=True)

                # Run python -m gitgud.main check
                env = os.environ.copy()
                env["PYTHONPATH"] = self.project_root
                res = subprocess.run(
                    ["python", "-m", "gitgud.main", "check"],
                    cwd=repo,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                )
                self.assertEqual(res.returncode, 1)
                self.assertIn("COMMIT REJECTED", res.stdout)
                self.assertIn("Needs work.", res.stdout)
            finally:
                shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
