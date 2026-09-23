import os
import unittest
from unittest.mock import MagicMock, patch

from gpt_researcher.scraper.anysearch_extract.anysearch_extract import (
    AnySearchExtract,
)


class TestAnySearchExtract(unittest.TestCase):
    @patch("gpt_researcher.scraper.anysearch_extract.anysearch_extract.requests.post")
    def test_scrape_returns_content_and_title(self, mock_post):
        mock_post.return_value = MagicMock(
            json=MagicMock(
                return_value={
                    "code": 0,
                    "message": "success",
                    "data": {
                        "url": "https://example.com",
                        "title": "Example Domain",
                        "content": "# Example Domain\n\nLong enough content body.",
                    },
                }
            )
        )

        with patch.dict(os.environ, {}, clear=True):
            content, images, title = AnySearchExtract("https://example.com").scrape()

        mock_post.assert_called_once_with(
            "https://api.anysearch.com/v1/extract",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Anysearch-Client": "gpt-researcher",
            },
            json={"url": "https://example.com"},
            timeout=30,
        )
        self.assertEqual(title, "Example Domain")
        self.assertIn("Example Domain", content)
        self.assertEqual(images, [])

    @patch("gpt_researcher.scraper.anysearch_extract.anysearch_extract.requests.post")
    def test_bearer_header_when_api_key_set(self, mock_post):
        mock_post.return_value = MagicMock(json=MagicMock(return_value={"code": 0}))

        with patch.dict(os.environ, {"ANYSEARCH_API_KEY": "as_sk_test"}, clear=True):
            AnySearchExtract("https://example.com").scrape()

        headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer as_sk_test")

    @patch("gpt_researcher.scraper.anysearch_extract.anysearch_extract.requests.post")
    def test_application_error_code_returns_empty_tuple(self, mock_post):
        mock_post.return_value = MagicMock(
            json=MagicMock(return_value={"code": -1, "message": "Rate limited"})
        )

        with patch.dict(os.environ, {}, clear=True):
            result = AnySearchExtract("https://example.com").scrape()

        self.assertEqual(result, ("", [], ""))

    @patch("gpt_researcher.scraper.anysearch_extract.anysearch_extract.requests.post")
    def test_empty_content_returns_empty_tuple(self, mock_post):
        mock_post.return_value = MagicMock(
            json=MagicMock(return_value={"code": 0, "data": {"title": "T", "content": ""}})
        )

        with patch.dict(os.environ, {}, clear=True):
            result = AnySearchExtract("https://example.com").scrape()

        self.assertEqual(result, ("", [], ""))

    @patch("gpt_researcher.scraper.anysearch_extract.anysearch_extract.requests.post")
    def test_connection_error_returns_empty_tuple(self, mock_post):
        mock_post.side_effect = Exception("connection refused")

        with patch.dict(os.environ, {}, clear=True):
            result = AnySearchExtract("https://example.com").scrape()

        self.assertEqual(result, ("", [], ""))


if __name__ == "__main__":
    unittest.main()
