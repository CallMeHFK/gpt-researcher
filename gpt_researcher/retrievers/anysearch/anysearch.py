# AnySearch Search Retriever

# libraries
import logging
import os

import requests


class AnySearchRetriever:
    """
    AnySearch API Retriever

    AnySearch works anonymously without an API key (with lower rate limits);
    set the ANYSEARCH_API_KEY environment variable for higher limits.
    ANYSEARCH_TAG optionally switches to vertical domain search, using the
    ``domain.sub_domain`` form (e.g. ``finance.quotes``).
    """

    def __init__(self, query, query_domains=None):
        """
        Initializes the AnySearchRetriever object.
        Args:
            query: The search query.
            query_domains: Accepted for retriever interface compatibility;
                domain scoping is done through ANYSEARCH_TAG instead.
        """
        self.query = query
        self.query_domains = query_domains or None
        self.api_key = os.environ.get("ANYSEARCH_API_KEY") or None
        self.base_url = (
            os.environ.get("ANYSEARCH_API_BASE_URL") or "https://api.anysearch.com"
        ).rstrip("/")
        self.tag = os.environ.get("ANYSEARCH_TAG") or None
        self.logger = logging.getLogger(__name__)

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Anysearch-Client": "gpt-researcher",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def search(self, max_results=7) -> list[dict[str, str]]:
        """
        Searches the query using the AnySearch API.
        Args:
            max_results: The maximum number of results to return.
        Returns:
            A list of search results normalized like the other retrievers.
        """
        url = f"{self.base_url}/v1/search"
        payload = {
            "query": self.query,
            # AnySearch accepts between 1 and 10 results per request.
            "max_results": max(1, min(int(max_results), 10)),
        }
        if self.tag:
            payload["tag"] = self.tag

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=20
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                self.logger.error(
                    "Unexpected AnySearch response type. Resulting in empty response."
                )
                return []
            # The API reports application-level failures with a non-zero
            # `code` even on HTTP 200, so check both.
            if body.get("code", 0) != 0:
                self.logger.error(
                    f"AnySearch search failed: {body.get('message')}. "
                    "Resulting in empty response."
                )
                return []
            data = body.get("data") or {}
            if not isinstance(data, dict):
                return []
            results = data.get("results") or []
            if not isinstance(results, list):
                return []
        except Exception as e:
            self.logger.error(
                f"Error fetching AnySearch search results: {e}. "
                "Resulting in empty response."
            )
            return []

        search_results = []

        # Normalize the results to match the format of the other search APIs
        for result in results:
            if not isinstance(result, dict):
                continue
            href = result.get("url")
            if not href:
                continue
            search_result = {
                "title": result.get("title") or "",
                "href": href,
                "body": result.get("snippet") or result.get("content") or "",
            }
            search_results.append(search_result)

        return search_results
