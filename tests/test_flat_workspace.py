"""Presentation-only coverage and cascade tests. Never imports the Flask app.

Optional real Chromium checks:
PLAYWRIGHT_CORE_PATH=/path/to/playwright-core \
CHROMIUM_EXECUTABLE_PATH=/path/to/chrome python -m unittest tests.test_flat_workspace
"""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import unittest

from jinja2 import Environment, FileSystemLoader, meta, nodes


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static/css/flat-workspace.css"
ENTRYPOINT = "_flat_workspace_styles.html"


class FlatWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(ROOT / "templates"))
        # Application filter registration is intentionally not imported.
        self.env.filters["clean_ai_analysis"] = lambda value: value

    def references(self, name, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            return seen
        seen.add(name)
        source = (ROOT / "templates" / name).read_text()
        tree = self.env.parse(source)
        references = set(meta.find_referenced_templates(tree))
        # Jinja meta returns None for the responsive detail view's conditional
        # extends expression. Both branches must inherit the shared entrypoint.
        for extension in tree.find_all(nodes.Extends):
            for constant in extension.template.find_all(nodes.Const):
                if isinstance(constant.value, str) and constant.value.endswith(".html"):
                    references.add(constant.value)
        for reference in references:
            if reference:
                self.references(reference, seen)
        return seen

    def test_every_live_render_template_reaches_shared_sheet(self):
        inventory = set()
        for path in ROOT.glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else None)
                if name == "render_template" and node.args:
                    value = node.args[0]
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        inventory.add(value.value)
        self.assertGreaterEqual(len(inventory), 33)
        for name in sorted(inventory):
            with self.subTest(template=name):
                self.assertIn(ENTRYPOINT, self.references(name))

    def test_all_document_roots_opt_in_and_dormant_pages_inherit(self):
        for path in (ROOT / "templates").rglob("*.html"):
            source = path.read_text()
            root = re.search(r"<html\b[^>]*>", source)
            if root:
                with self.subTest(template=str(path)):
                    self.assertIn("data-flat-workspace", root.group())
        for name in ("register.html", "tickets/mobile_view_ticket.html"):
            self.assertIn(ENTRYPOINT, self.references(name))

    def test_all_jinja_templates_compile(self):
        for name in self.env.list_templates(extensions=["html"]):
            with self.subTest(template=name):
                self.env.get_template(name)

    def test_scope_does_not_reset_icons_charts_or_checkboxes(self):
        source = CSS.read_text()
        self.assertNotRegex(source, r"\*\s*(?::[^{]+)?\s*\{")
        self.assertNotRegex(source, r"\bstroke(?:-width)?\s*:")
        self.assertNotRegex(source, r"\bappearance\s*:")
        self.assertNotRegex(source, r"(?<![-\w])(?:overflow|height|grid-template-(?:rows|columns|areas))\s*:")
        self.assertNotIn(".ti-volume", source)
        self.assertIn("body :focus-visible", source)
        self.assertIn('input[type="checkbox"]', source)
        self.assertIn('input[type="radio"]', source)
        self.assertIn("border-color: var(--flat-check) !important", source)

    def test_dashboard_and_schedule_geometry_contracts(self):
        dashboard = (ROOT / "templates/dashboard.html").read_text()
        self.assertIn('"people timeline bookings" "people tickets bookings"', dashboard)
        self.assertRegex(dashboard, r"#ccTicketsList\s*\{[^}]*height:\s*0;[^}]*flex:\s*1 1 0;")
        self.assertIn('role="region" aria-label="Active tickets"', dashboard)
        self.assertIn("cur.scrollTop = scrollTop", dashboard)
        schedules = (ROOT / "static/css/style.css").read_text()
        self.assertRegex(schedules, r"#schedule-view \.day-column\s*\{[^}]*height:\s*1504px;")
        self.assertRegex(schedules, r"#schedule-view \.time-column\s*\{[^}]*height:\s*1504px;")
        for name in ("calendar.html", "personal_schedule.html"):
            self.assertIn("js/schedule-height.js", (ROOT / "templates" / name).read_text())

    def test_dark_and_light_palette_contrast(self):
        source = CSS.read_text()
        dark, light = re.findall(r"--flat-ink:\s*(#[0-9a-f]+);", source)
        surfaces = re.findall(r"--flat-(?:canvas|blue|green|plum|amber|input):\s*(#[0-9a-f]+);", source)

        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))

        for ink, shades in ((dark, surfaces[:6]), (light, surfaces[6:])):
            for shade in shades:
                values = sorted((luminance(ink), luminance(shade)))
                self.assertGreater((values[1] + .05) / (values[0] + .05), 4.5)

    @unittest.skipUnless(os.getenv("PLAYWRIGHT_CORE_PATH") and os.getenv("CHROMIUM_EXECUTABLE_PATH"),
                         "Set browser paths to run the offline computed-style regression.")
    def test_browser_computed_cascade_and_affordances(self):
        # Put the new sheet FIRST, and all old styles after it. This deliberately
        # tests specificity, not a fortunate network/load order.
        fixtures = {}
        pages = [
            "base.html", "mobile_base_enhanced.html", "auth_base.html",
            "dashboard.html", "tickets/dashboard.html", "tickets/_view_styles.html",
            "admin/dashboard.html", "mobile/calendar.html",
            "mobile/personal_schedule.html", "mobile/quick_links.html", "login.html",
            "tickets/feedback.html", "api/docs.html",
        ]
        for theme in ("dark", "light"):
            user = SimpleNamespace(is_authenticated=True, theme_preference=theme)
            legacy = []
            for page in pages:
                for style in re.findall(r"<style[^>]*>(.*?)</style>", (ROOT / "templates" / page).read_text(), re.S):
                    rendered = self.env.from_string(style).render(current_user=user)
                    legacy.append(re.sub(r"@import[^;]+;", "", rendered))
            styles = ["style.css", f"{theme}-theme.css", "ticket-insights.css", "api-access.css", "standalone-theme.css"]
            fixtures[theme] = CSS.read_text() + "\n" + "\n".join(
                (ROOT / "static/css" / name).read_text() for name in styles
            ) + "\n" + "\n".join(legacy)
        result = subprocess.run(
            ["node", str(ROOT / "tests/flat_workspace_browser.cjs")],
            input=json.dumps(fixtures), text=True, capture_output=True,
            check=False, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
