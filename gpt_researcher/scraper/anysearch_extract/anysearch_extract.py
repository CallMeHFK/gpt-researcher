# AnySearch Extract Scraper

import logging
import os

import requests


class AnySearchExtract:
    """
    Extracts clean markdown content from a URL through the AnySearch
    extract API. Works anonymously without an API key (with lower rate
    limits); set the ANYSEARCH_API_KEY environment variable for higher
    limits.
    """

    def __init__(self, link, session=None):
        self.link = link
        self.session = session
        self.api_key = os.environ.get("ANYSEARCH_API_KEY") or None
        self.base_url = (
            os.environ.get("ANYSEARCH_API_BASE_URL") or "https://api.anysearch.com"
        ).rstrip("/")
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

    def scrape(self) -> tuple:
        """
        This function extracts content from a specified link using the
        AnySearch extract API.

        Returns:
            The `scrape` method returns a tuple containing the extracted
            content, a list of image URLs, and the title of the webpage.
            The extract endpoint returns markdown without images, so the
            image list is always empty. If any exception occurs during the
            process, an error message is logged and an empty result is
            returned.
        """
        try:
            response = requests.post(
                f"{self.base_url}/v1/extract",
                headers=self._get_headers(),
                json={"url": self.link},
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            # Application-level failures carry a non-zero `code` even on
            # HTTP 200, so check both the envelope and the payload shape.
            if not isinstance(body, dict) or body.get("code", 0) != 0:
                message = (
                    body.get("message")
                    if isinstance(body, dict)
                    else "malformed response"
                )
                self.logger.error(
                    f"AnySearch extract failed for {self.link}: {message}"
                )
                return "", [], ""

            data = body.get("data") or {}
            if not isinstance(data, dict):
                return "", [], ""
            content = data.get("content") or ""
            title = data.get("title") or ""
            if not content:
                return "", [], ""

            return content, [], title
        except Exception as e:
            self.logger.error("Error! : " + str(e))
            return "", [], ""
