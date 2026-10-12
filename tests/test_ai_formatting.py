import unittest
from ai_text import format_ai_response


class AIFormattingTests(unittest.TestCase):
    def test_saved_plain_text(self):
        result = format_ai_response("Summary\nEncoder is not working.\n\nPossible Causes (Ranked)\n1. Crash\n2. Resources\n\nSafe Diagnostic Steps\n1. Ask for the error.")
        self.assertIn("<h5>Summary</h5>", result)
        self.assertIn("<h5>Possible Causes (Ranked)</h5>", result)
        self.assertIn('<ol start="1"><li>Crash</li><li>Resources</li></ol>', result)
        self.assertIn("<p>Encoder is not working.</p>", result)

    def test_markdown(self):
        result = format_ai_response("## Next steps\n- **Check** the `encoder`\n- Retry")
        self.assertIn("<h5>Next steps</h5>", result)
        self.assertIn("<ul><li><strong>Check</strong> the <code>encoder</code></li>", result)

    def test_untrusted_html_is_not_executable(self):
        result = format_ai_response('## <img src=x onerror=alert(1)>\n<script>alert(1)</script>')
        self.assertNotIn("<img", result)
        self.assertNotIn("<script", result)
        self.assertIn("&lt;script&gt;", result)

    def test_line_breaks_and_paragraphs(self):
        self.assertEqual(format_ai_response("First\nSecond\n\nThird"),
                         "<p>First<br>Second</p><p>Third</p>")

    def test_no_content_or_emojis(self):
        self.assertEqual(format_ai_response(None), "")
        self.assertNotIn("🤖", format_ai_response("🤖 Summary\nTest"))


if __name__ == "__main__":
    unittest.main()
