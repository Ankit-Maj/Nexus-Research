"""
Tavily search client with:
  - Multi-key rotation (TAVILY_API_KEY, TAVILY_API_KEY2, …)
  - DuckDuckGo HTML scrape as final fallback
  - In-memory result cache to avoid duplicate API calls
"""

import httpx
import asyncio
from typing import List, Dict, Any
from app.utils.config import TAVILY_API_KEYS, logger

TAVILY_API_URL = "https://api.tavily.com/search"
DDGO_URL = "https://html.duckduckgo.com/html/"


class TavilySearchClient:
    def __init__(self):
        self._keys: List[str] = list(TAVILY_API_KEYS)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_async(
        self, query: str, max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Search with Tavily (key rotation) then DuckDuckGo fallback."""
        cache_key = f"{query}|{max_results}"
        if cache_key in self._cache:
            logger.info(f"[Tavily] Cache hit for: '{query}'")
            return self._cache[cache_key]

        # Try each Tavily key in order
        for idx, api_key in enumerate(self._keys):
            try:
                results = await self._tavily_search(api_key, query, max_results)
                if results:
                    self._cache[cache_key] = results
                    return results
                logger.warning(
                    f"[Tavily] Key #{idx + 1} returned empty results for '{query}'."
                )
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate" in err_str or "quota" in err_str:
                    logger.warning(
                        f"[Tavily] Key #{idx + 1} rate-limited. Trying next key."
                    )
                else:
                    logger.error(f"[Tavily] Key #{idx + 1} error: {e}")

        # DuckDuckGo fallback
        logger.warning("[Tavily] All keys exhausted. Falling back to DuckDuckGo.")
        try:
            results = await self._ddgo_search(query, max_results)
            if results:
                self._cache[cache_key] = results
            return results
        except Exception as e:
            logger.error(f"[Tavily] DuckDuckGo fallback also failed: {e}")
            return []

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _tavily_search(
        self, api_key: str, query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(TAVILY_API_URL, json=payload)
            if response.status_code == 429:
                raise Exception("429 rate limit")
            if response.status_code != 200:
                raise Exception(
                    f"Tavily HTTP {response.status_code}: {response.text[:200]}"
                )
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append(
                    {
                        "title": item.get("title", "Web Result"),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0),
                    }
                )
            logger.info(
                f"[Tavily] Retrieved {len(results)} results for '{query}'."
            )
            return results

    async def _ddgo_search(
        self, query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Minimal DuckDuckGo HTML scrape — no JS, no API key required."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        }
        params = {"q": query, "kl": "us-en"}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(DDGO_URL, data=params, headers=headers)
            resp.raise_for_status()

        # Very lightweight HTML parse — no BeautifulSoup dependency
        html = resp.text
        results: List[Dict[str, Any]] = []
        # Extract result blocks between <a class="result__a" href="...">
        import re

        links = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        snippets = re.findall(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL
        )

        for i, (url, title) in enumerate(links[:max_results]):
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
            results.append(
                {
                    "title": clean_title or "DuckDuckGo Result",
                    "url": url,
                    "content": snippet,
                    "score": 0.5,
                }
            )

        logger.info(f"[DuckDuckGo] Retrieved {len(results)} results for '{query}'.")
        return results


# Singleton
tavily_client = TavilySearchClient()
