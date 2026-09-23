# AnySearch Integration

This page documents how the AnySearch integration is wired into GPT Researcher, for users and for maintainers who need to touch it later.

## What it provides

| Capability | Entry point | Env |
| --- | --- | --- |
| General web search | `RETRIEVER=anysearch` (`gpt_researcher/retrievers/anysearch/`) | `ANYSEARCH_API_KEY` (optional), `ANYSEARCH_TAG` (optional) |
| Vertical domain search | same retriever, with `ANYSEARCH_TAG` set | `ANYSEARCH_TAG=domain.sub_domain` |
| Page content extraction (markdown) | `SCRAPER=anysearch_extract` (`gpt_researcher/scraper/anysearch_extract/`) | `ANYSEARCH_API_KEY` (optional) |

Both components work **anonymously** — no API key is required. Requests without a key are rate-limited more aggressively; a free key at [anysearch.com/console/api-keys](https://anysearch.com/console/api-keys) raises the limits and is sent as `Authorization: Bearer <key>`.

Parallel search is inherited from GPT Researcher: subtopic queries already run concurrently, and each call fans out to one `/v1/search` request per retriever invocation.

## Configuration

```bash
# Search
RETRIEVER=anysearch
ANYSEARCH_API_KEY=as_sk_xxx      # optional; anonymous without it
ANYSEARCH_TAG=finance.quotes     # optional; see https://api.anysearch.com/v1/sub-domains

# Scraping (independent of the retriever choice)
SCRAPER=anysearch_extract
```

`ANYSEARCH_API_BASE_URL` overrides the API base (default `https://api.anysearch.com`), mainly for tests or proxies.

`ANYSEARCH_TAG` must be a `domain.sub_domain` string (bare domains such as `finance` are rejected by the API). `GET /v1/sub-domains?domain=finance` lists valid values per domain.

## API surface used

- `POST /v1/search` — body `{query, max_results, tag?}`; `max_results` is clamped to 1–10. Response: `{"code": 0, "data": {"results": [{title, url, snippet, content}]}}`.
- `POST /v1/extract` — body `{url}`. Response: `{"code": 0, "data": {url, title, content}}` where `content` is markdown.

Every request sends `Content-Type: application/json`, `Accept: application/json` and an `X-Anysearch-Client: gpt-researcher` header (AnySearch uses it to attribute traffic; it carries no secrets).

## Error handling contract

AnySearch reports application-level failures with a non-zero `code` in the envelope even when the HTTP status is 200 (for example `code: -1`, `message: "Rate limited, retry after 300 seconds."`). Both components treat this like a transport error:

- retriever: log at `ERROR` and return `[]`, so the run falls back to other configured retrievers or an empty source list;
- scraper: log at `ERROR` and return `("", [], "")`, which the `Scraper` pipeline rejects as an empty source.

Results missing a `url` are skipped rather than crashing the normalization loop. This mirrors how the Brave and Tavily-Extract backends behave.

## File map

| File | Role |
| --- | --- |
| `gpt_researcher/retrievers/anysearch/anysearch.py` | `AnySearchRetriever` (search) |
| `gpt_researcher/retrievers/__init__.py` | package export |
| `gpt_researcher/actions/retriever.py` | `case "anysearch"` in the retriever factory |
| `gpt_researcher/scraper/anysearch_extract/anysearch_extract.py` | `AnySearchExtract` (scrape) |
| `gpt_researcher/scraper/scraper.py` | `SCRAPER_CLASSES["anysearch_extract"]` |
| `tests/test_anysearch_retriever.py` | retriever unit tests (fully mocked) |
| `tests/test_anysearch_extract_scraper.py` | scraper unit tests (fully mocked) |

## Running the tests

The tests patch `requests.post` and never touch the network, so they pass under the CI setting `GPTR_BLOCK_NETWORK=1`:

```bash
python -m pytest tests/test_anysearch_retriever.py tests/test_anysearch_extract_scraper.py
```

## Smoke test against the live API

```bash
export RETRIEVER=anysearch
python - <<'PY'
from gpt_researcher.retrievers import AnySearchRetriever
print(AnySearchRetriever("open source ai agent frameworks").search(max_results=3))
PY
```

Anonymous quota is small; a 429-style envelope here is expected behavior, not an integration bug.
