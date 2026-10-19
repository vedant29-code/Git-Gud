"""Unit tests for diff collection, filtering, truncation, and normalization."""

import os
import tempfile
import unittest
from unittest.mock import patch

from gitgud.diff import (
    _parse_diff_blocks,
    get_staged_diff,
    is_merge_or_rebase,
    matches_any_pattern,
)


SAMPLE_MULTI_DIFF = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,5 @@
+import os
+import sys
 def main():
-    pass
+    print("Hello world")
diff --git a/package-lock.json b/package-lock.json
index 3333333..4444444 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,3 +1,4 @@
+{ "lockfileVersion": 2 }
diff --git a/static/bundle.min.js b/static/bundle.min.js
index 5555555..6666666 100644
--- a/static/bundle.min.js
+++ b/static/bundle.min.js
@@ -1 +1 @@
-var a=1;
+var a=2;
diff --git a/assets/logo.png b/assets/logo.png
index 7777777..8888888 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""


class TestDiff(unittest.TestCase):
    def test_matches_any_pattern(self):
        patterns = [
            "package-lock.json",
            "*.min.js",
            "*.png",
            "vendor/*",
            "node_modules/",
        ]

        self.assertTrue(matches_any_pattern("package-lock.json", patterns))
        self.assertTrue(matches_any_pattern("deep/nested/package-lock.json", patterns))
        self.assertTrue(matches_any_pattern("assets/bundle.min.js", patterns))
        self.assertTrue(matches_any_pattern("images/icon.png", patterns))
        self.assertTrue(matches_any_pattern("vendor/lib/plugin.py", patterns))
        self.assertTrue(matches_any_pattern("node_modules/pkg/index.js", patterns))

        self.assertFalse(matches_any_pattern("src/main.py", patterns))
        self.assertFalse(matches_any_pattern("styles/app.css", patterns))

    def test_parse_diff_blocks(self):
        blocks = _parse_diff_blocks(SAMPLE_MULTI_DIFF)
        self.assertEqual(len(blocks), 4)

        # src/app.py
        self.assertEqual(blocks[0].path, "src/app.py")
        self.assertEqual(blocks[0].added_lines, 3)
        self.assertEqual(blocks[0].deleted_lines, 1)
        self.assertFalse(blocks[0].is_binary)

        # package-lock.json
        self.assertEqual(blocks[1].path, "package-lock.json")

        # Binary file
        self.assertEqual(blocks[3].path, "assets/logo.png")
        self.assertTrue(blocks[3].is_binary)

    def test_crlf_normalization(self):
        crlf_diff = SAMPLE_MULTI_DIFF.replace("\n", "\r\n")
        blocks = _parse_diff_blocks(crlf_diff)
        self.assertEqual(len(blocks), 4)
        self.assertNotIn("\r", blocks[0].content)

    def test_get_staged_diff_filters_noise(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = SAMPLE_MULTI_DIFF.encode("utf-8")
            mock_run.return_value.stderr = b""

            patterns = ["package-lock.json", "*.min.js", "*.png"]
            res = get_staged_diff(ignore_patterns=patterns, max_diff_chars=10000)

            self.assertIsNone(res.skip_reason)
            self.assertEqual(res.total_files, 4)
            self.assertEqual(res.included_files, 1)
            self.assertEqual(res.ignored_files, 3)
            self.assertIn("src/app.py", res.diff_text)
            self.assertNotIn("package-lock.json", res.diff_text)
            self.assertNotIn("bundle.min.js", res.diff_text)

    def test_diff_truncation_budget(self):
        large_file_diff = "diff --git a/big.py b/big.py\n" + ("+line\n" * 500)
        small_file_diff = "diff --git a/small.py b/small.py\n+small\n"
        combined = large_file_diff + small_file_diff

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = combined.encode("utf-8")
            mock_run.return_value.stderr = b""

            # Set small budget (1000 chars)
            res = get_staged_diff(ignore_patterns=[], max_diff_chars=1000)

            self.assertTrue(res.is_truncated)
            self.assertIn("truncated", res.diff_text)
            self.assertLessEqual(len(res.diff_text), 1600)

    def test_empty_diff_skips(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = b"   \n  \n"
            mock_run.return_value.stderr = b""

            res = get_staged_diff()
            self.assertIsNotNone(res.skip_reason)
            self.assertIn("Empty", res.skip_reason)

    def test_gitgud_skip_env_var(self):
        with patch.dict(os.environ, {"GITGUD_SKIP": "1"}):
            res = get_staged_diff()
            self.assertIsNotNone(res.skip_reason)
            self.assertIn("GITGUD_SKIP", res.skip_reason)

    def test_merge_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            merge_head = os.path.join(tmp_dir, "MERGE_HEAD")
            with open(merge_head, "w") as f:
                f.write("abc1234\n")

            self.assertTrue(is_merge_or_rebase(tmp_dir))


if __name__ == "__main__":
    unittest.main()
