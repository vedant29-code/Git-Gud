"""Unit tests for terminal rendering and styling."""

import os
import unittest
from unittest.mock import patch

from gitgud.judge import Issue, JudgeResult
from gitgud.render import (
    Style,
    render_issues_list,
    render_report,
    render_roast_box,
    render_score_meter,
    render_verdict_banner,
    supports_color,
)


class TestRender(unittest.TestCase):
    def test_no_color_env(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(supports_color())

    def test_style_disabled_has_no_ansi(self):
        style = Style(enabled=False)
        self.assertEqual(style.RED, "")
        self.assertEqual(style.BOLD, "")
        self.assertEqual(style.RESET, "")

    def test_style_enabled_has_ansi(self):
        style = Style(enabled=True)
        self.assertIn("\033[", style.RED)
        self.assertIn("\033[", style.RESET)

    def test_score_meter(self):
        style = Style(enabled=False)
        high = render_score_meter(9.0, style)
        self.assertIn("[=========.]", high)
        self.assertIn("9.0/10.0", high)

        perfect = render_score_meter(10.0, style)
        self.assertIn("[==========]", perfect)
        self.assertIn("10.0/10.0", perfect)

        low = render_score_meter(2.0, style)
        self.assertIn("[==........]", low)
        self.assertIn("2.0/10.0", low)

    def test_roast_box(self):
        style = Style(enabled=False)
        box = render_roast_box("This code is a disaster.", width=60, style=style)
        self.assertIn("THE JUDGE'S ROAST", box)
        self.assertIn("This code is a disaster.", box)
        self.assertIn("┌", box)
        self.assertIn("└", box)

    def test_issues_list(self):
        style = Style(enabled=False)
        issues = [
            Issue(
                file="main.py",
                line=42,
                severity="high",
                problem="SQL Injection vulnerability",
                fix="Use parameterized queries",
            ),
            Issue(
                file="utils.py",
                line=12,
                severity="low",
                problem="Unused import",
                fix="Remove import",
            ),
        ]
        rendered = render_issues_list(issues, width=70, style=style)
        self.assertIn("[HIGH CRITICAL]", rendered)
        self.assertIn("main.py:42", rendered)
        self.assertIn("SQL Injection vulnerability", rendered)
        self.assertIn("Use parameterized queries", rendered)
        self.assertIn("[LOW NITPICK]", rendered)

    def test_verdict_banner(self):
        style = Style(enabled=False)
        approved = render_verdict_banner("approve", width=50, style=style)
        self.assertIn("COMMIT APPROVED", approved)

        rejected = render_verdict_banner("reject", width=50, style=style)
        self.assertIn("COMMIT REJECTED", rejected)
        self.assertIn("--no-verify", rejected)

    def test_full_report_render(self):
        res = JudgeResult(
            success=True,
            verdict="approve",
            score=8.5,
            roast="Impressive code structure.",
            issues=[],
        )
        report = render_report(res, model_name="phi3")
        self.assertIn("GIT-GUD AI", report)
        self.assertIn("Model: phi3", report)
        self.assertIn("Impressive code structure.", report)
        self.assertIn("COMMIT APPROVED", report)


if __name__ == "__main__":
    unittest.main()
