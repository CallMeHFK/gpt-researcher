import os
import unittest
from unittest.mock import MagicMock, patch

from gpt_researcher.retrievers.anysearch.anysearch import AnySearchRetriever


def _envelope(results):
    return MagicMock(
        json=MagicMock(
            return_value={"code": 0, "message": "success", "data": {"results": results}}
        )
    )


class TestAnySearchRetriever(unittest.TestCase):
    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_search_normalizes_results(self, mock_post):
        mock_post.return_value = _envelope(
            [
                {
                    "title": "One",
                    "url": "https://example.com/one",
                    "snippet": "First snippet",
                    "content": "First longer content",
                },
                {
                    "title": "Two",
                    "url": "https://example.com/two",
                    "snippet": "Second snippet",
                },
            ]
        )

        with patch.dict(os.environ, {}, clear=True):
            results = AnySearchRetriever("test query").search(max_results=2)

        mock_post.assert_called_once_with(
            "https://api.anysearch.com/v1/search",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Anysearch-Client": "gpt-researcher",
            },
            json={"query": "test query", "max_results": 2},
            timeout=20,
        )
        self.assertEqual(
            results,
            [
                {
                    "title": "One",
                    "href": "https://example.com/one",
                    "body": "First snippet",
                },
                {
                    "title": "Two",
                    "href": "https://example.com/two",
                    "body": "Second snippet",
                },
            ],
        )

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_anonymous_without_api_key(self, mock_post):
        mock_post.return_value = _envelope([])

        with patch.dict(os.environ, {}, clear=True):
            AnySearchRetriever("test query").search()

        headers = mock_post.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", headers)

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_bearer_header_when_api_key_set(self, mock_post):
        mock_post.return_value = _envelope([])

        with patch.dict(os.environ, {"ANYSEARCH_API_KEY": "as_sk_test"}, clear=True):
            AnySearchRetriever("test query").search()

        headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer as_sk_test")

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_tag_env_enables_vertical_search(self, mock_post):
        mock_post.return_value = _envelope([])

        with patch.dict(os.environ, {"ANYSEARCH_TAG": "finance.quotes"}, clear=True):
            AnySearchRetriever("tesla earnings").search()

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["tag"], "finance.quotes")

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_max_results_clamped_to_api_range(self, mock_post):
        mock_post.return_value = _envelope([])

        with patch.dict(os.environ, {}, clear=True):
            AnySearchRetriever("test query").search(max_results=50)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["max_results"], 10)

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_application_error_code_returns_empty(self, mock_post):
        mock_post.return_value = MagicMock(
            json=MagicMock(return_value={"code": -1, "message": "Rate limited"})
        )

        with patch.dict(os.environ, {}, clear=True):
            results = AnySearchRetriever("test query").search()

        self.assertEqual(results, [])

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_malformed_payload_returns_empty(self, mock_post):
        mock_post.return_value = MagicMock(json=MagicMock(return_value={"code": 0}))

        with patch.dict(os.environ, {}, clear=True):
            results = AnySearchRetriever("test query").search()

        self.assertEqual(results, [])

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_connection_error_returns_empty(self, mock_post):
        mock_post.side_effect = Exception("connection refused")

        with patch.dict(os.environ, {}, clear=True):
            results = AnySearchRetriever("test query").search()

        self.assertEqual(results, [])

    @patch("gpt_researcher.retrievers.anysearch.anysearch.requests.post")
    def test_results_without_url_are_skipped(self, mock_post):
        mock_post.return_value = _envelope(
            [
                {"title": "No url", "snippet": "x"},
                {"title": "Ok", "url": "https://example.com", "snippet": "y"},
            ]
        )

        with patch.dict(os.environ, {}, clear=True):
            results = AnySearchRetriever("test query").search()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["href"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
