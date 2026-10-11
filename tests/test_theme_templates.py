"""Presentation-only checks; no Flask app, database, or preference writes."""
import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import unittest

from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]


class ThemeTemplateTests(unittest.TestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(ROOT / "templates"))
        self.env.globals.update(
            url_for=lambda endpoint, **kwargs: "/static/" + kwargs.get("filename", ""),
            csrf_token=lambda: "presentation-test",
        )

    def test_all_templates_parse(self):
        for template in (ROOT / "templates").rglob("*.html"):
            with self.subTest(template=str(template.relative_to(ROOT))):
                self.env.parse(template.read_text())

    def test_standalone_themes_and_system_changes(self):
        for saved in (None, "light", "dark"):
            user = SimpleNamespace(is_authenticated=saved is not None, theme_preference=saved)
            html = self.env.get_template("_standalone_theme.html").render(current_user=user)
            script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
            for system_light in (True, False):
                with self.subTest(saved=saved, system_light=system_light):
                    expected = saved or ("light" if system_light else "dark")
                    changed = saved or ("dark" if system_light else "light")
                    harness = """
const system = {matches: SYSTEM, addEventListener: (_, cb) => {system.change = cb;}};
const attributes = {};
const bodyClasses = {};
global.window = {matchMedia: () => system};
global.document = {
  documentElement: {setAttribute: (key, value) => {attributes[key] = value;}},
  body: {classList: {toggle: (key, value) => {bodyClasses[key] = value;}}},
  addEventListener: (_, cb) => cb()
};
SCRIPT
if (attributes['data-bs-theme'] !== EXPECTED) throw Error('Initial theme mismatch');
if (bodyClasses['light-theme'] !== (EXPECTED === 'light')) throw Error('Body theme mismatch');
system.matches = !system.matches;
system.change();
if (attributes['data-bs-theme'] !== CHANGED) throw Error('System change mismatch');
"""
                    harness = harness.replace("SYSTEM", json.dumps(system_light)).replace(
                        "SCRIPT", script
                    ).replace("EXPECTED", json.dumps(expected)).replace("CHANGED", json.dumps(changed))
                    subprocess.run(["node", "-"], input=harness, text=True, check=True, capture_output=True)

    def test_public_templates_render_and_script_syntax(self):
        for saved in (None, "light", "dark"):
            user = SimpleNamespace(is_authenticated=saved is not None, theme_preference=saved)
            for state in ("open", "submitted", "expired"):
                html = self.env.get_template("tickets/feedback.html").render(
                    current_user=user, state=state, ticket_number=17, form_error="Please select a rating."
                )
                self.assertIn('class="survey-page"', html)
                self.assertIn("standalone-theme.css", html)
                for script in re.findall(r"<script>(.*?)</script>", html, re.S):
                    subprocess.run(["node", "--check"], input=script, text=True, check=True, capture_output=True)
            html = self.env.get_template("api/docs.html").render(
                current_user=user,
                spec={"paths": {}, "components": {"schemas": {
                    "TicketInput": {}, "ScheduleInput": {}, "ContentInput": {}
                }}},
            )
            self.assertIn('class="api-docs"', html)
            self.assertIn("standalone-theme.css", html)


if __name__ == "__main__":
    unittest.main()
