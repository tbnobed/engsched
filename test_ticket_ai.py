"""No network calls: exercise OpenAI response and failure handling."""
import unittest
from unittest.mock import Mock, patch

import requests
from app import app  # Initialize Flask before importing the blueprint.
from ticket_ai import ask_openai


class OpenAIResponseTests(unittest.TestCase):
    def call_with(self, status, payload=None):
        response = Mock(status_code=status)
        response.json.return_value = payload
        with patch("ticket_ai.requests.post", return_value=response):
            return ask_openai([{"role": "user", "content": "Test"}])

    def test_success(self):
        self.assertEqual(self.call_with(200, {
            "choices": [{"message": {"content": "Check the cable."}, "finish_reason": "stop"}]
        }), "Check the cable.")

    def test_auth_failure(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            self.call_with(401)

    def test_rate_limit(self):
        with self.assertRaisesRegex(ValueError, "usage or rate limit"):
            self.call_with(429)

    def test_server_failure(self):
        with self.assertRaisesRegex(ValueError, "HTTP 503"):
            self.call_with(503)

    def test_empty_answer(self):
        with self.assertRaisesRegex(ValueError, "no answer"):
            self.call_with(200, {"choices": [{"message": {"content": None}}]})

    def test_malformed_response(self):
        with self.assertRaisesRegex(ValueError, "invalid response"):
            self.call_with(200, {})

    def test_timeout(self):
        with patch("ticket_ai.requests.post", side_effect=requests.Timeout):
            with self.assertRaisesRegex(ValueError, "could not be reached"):
                ask_openai([])

    def test_truncation_is_disclosed(self):
        answer = self.call_with(200, {
            "choices": [{"message": {"content": "Partial"}, "finish_reason": "length"}]
        })
        self.assertIn("length limit", answer)


if __name__ == "__main__":
    unittest.main()
