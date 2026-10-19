"""Unit tests for configuration loading and precedence."""

import os
import tempfile
import unittest
from unittest.mock import patch

from gitgud.config import GitGudConfig, _parse_patterns, _to_bool, _to_float, _to_int, load_config


class TestConfig(unittest.TestCase):
    def setUp(self):
        # Clear any environment variables that might interfere
        self.env_keys = [
            "GITGUD_MODEL",
            "GITGUD_HOST",
            "GITGUD_TIMEOUT",
            "GITGUD_CONNECT_TIMEOUT",
            "GITGUD_THRESHOLD",
            "GITGUD_MAX_DIFF_CHARS",
            "GITGUD_ROAST_LEVEL",
            "GITGUD_STRICT",
            "GITGUD_IGNORE_PATTERNS",
            "GITGUD_LOG_FILE",
        ]
        self.orig_env = {k: os.environ.get(k) for k in self.env_keys}
        for k in self.env_keys:
            if k in os.environ:
                del os.environ[k]

    def tearDown(self):
        for k, v in self.orig_env.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

    def test_default_config(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            cfg = load_config(repo_root=empty_dir)
            self.assertEqual(cfg.model, "phi3")
            self.assertEqual(cfg.host, "http://localhost:11434")
            self.assertEqual(cfg.timeout, 60.0)
            self.assertEqual(cfg.connect_timeout, 3.0)
            self.assertEqual(cfg.threshold, 6.0)
            self.assertEqual(cfg.max_diff_chars, 12000)
            self.assertEqual(cfg.roast_level, "spicy")
            self.assertFalse(cfg.strict)
            self.assertIn("package-lock.json", cfg.ignore_patterns)

    def test_gitgud_file_parsing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = os.path.join(tmp_dir, ".gitgud")
            with open(config_file, "w") as f:
                f.write(
                    "model = llama3.2:3b\n"
                    "host = http://127.0.0.1:11435\n"
                    "threshold = 7.5\n"
                    "timeout = 45\n"
                    "max_diff_chars = 8000\n"
                    "roast_level = savage\n"
                    "strict = true\n"
                    "ignore_patterns = *.log, tmp/*\n"
                )

            cfg = load_config(repo_root=tmp_dir)
            self.assertEqual(cfg.model, "llama3.2:3b")
            self.assertEqual(cfg.host, "http://127.0.0.1:11435")
            self.assertEqual(cfg.threshold, 7.5)
            self.assertEqual(cfg.timeout, 45.0)
            self.assertEqual(cfg.max_diff_chars, 8000)
            self.assertEqual(cfg.roast_level, "savage")
            self.assertTrue(cfg.strict)
            self.assertIn("*.log", cfg.ignore_patterns)
            self.assertIn("tmp/*", cfg.ignore_patterns)

    def test_git_config_overrides_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = os.path.join(tmp_dir, ".gitgud")
            with open(config_file, "w") as f:
                f.write("model = phi3\nthreshold = 5.0\n")

            with patch("gitgud.config._get_git_config") as mock_git_cfg:
                def mock_lookup(key, root):
                    if key == "threshold":
                        return "8.2"
                    return None

                mock_git_cfg.side_effect = mock_lookup

                cfg = load_config(repo_root=tmp_dir)
                # Model should come from file
                self.assertEqual(cfg.model, "phi3")
                # Threshold should come from git config (overriding file)
                self.assertEqual(cfg.threshold, 8.2)

    def test_env_var_overrides_all(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = os.path.join(tmp_dir, ".gitgud")
            with open(config_file, "w") as f:
                f.write("model = phi3\nthreshold = 5.0\n")

            os.environ["GITGUD_MODEL"] = "mistral-nemo"
            os.environ["GITGUD_THRESHOLD"] = "9.5"

            with patch("gitgud.config._get_git_config") as mock_git_cfg:
                mock_git_cfg.return_value = "git-config-val"

                cfg = load_config(repo_root=tmp_dir)
                self.assertEqual(cfg.model, "mistral-nemo")
                self.assertEqual(cfg.threshold, 9.5)

    def test_type_conversions_and_fallbacks(self):
        self.assertTrue(_to_bool("true"))
        self.assertTrue(_to_bool("1"))
        self.assertTrue(_to_bool("YES"))
        self.assertFalse(_to_bool("false"))
        self.assertFalse(_to_bool("0"))
        self.assertFalse(_to_bool("invalid_bool", default=False))

        self.assertEqual(_to_float("7.2", 6.0), 7.2)
        self.assertEqual(_to_float("invalid", 6.0), 6.0)

        self.assertEqual(_to_int("15000", 12000), 15000)
        self.assertEqual(_to_int("invalid", 12000), 12000)

        patterns = _parse_patterns("a.txt, b.txt\nc.txt")
        self.assertEqual(patterns, ["a.txt", "b.txt", "c.txt"])


if __name__ == "__main__":
    unittest.main()
