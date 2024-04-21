from __future__ import annotations

import json

from sam.contrib import brave
from sam.utils import logger

from . import config


def search(query: str, _context=None) -> str:
    """
    Search the internet for information that matches the given query.

    The search is location aware and will return results based on the user's location.

    Args:
        query: The query to search for.
    """
    with brave.get_client() as api:
        if config.BRAVE_SEARCH_LATITUDE and config.BRAVE_SEARCH_LONGITUDE:
            api.headers.update(
                {
                    "X-Loc-Lat": str(config.BRAVE_SEARCH_LATITUDE),
                    "X-Loc-Long": str(config.BRAVE_SEARCH_LONGITUDE),
                }
            )
        try:
            results = api.search(query)["web"]
        except brave.BraveSearchAPIError:
            logger.exception("Failed to search the web for query: %s", query)
            return "search failed"
        else:
            if not results["results"]:
                logger.warning("No results found for query: %s", query)
                return "no results found"
            return json.dumps(
                {result["title"]: result["url"] for result in results["results"]}
            )
