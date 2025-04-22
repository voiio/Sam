from __future__ import annotations

import json
from urllib.parse import urljoin

from sam.contrib import algolia
from sam.utils import logger


def search(query: str, _context=None) -> str:
    """Search the platform for information that matches the given query.

    Args:
        query: The query to search for.
    """
    with algolia.get_client() as api:
        api.params.update(
            {
                "filters": "is_published:true",
                "attributesToRetrieve": [
                    "title",
                    "parent_object_title",
                    "public_url",
                    "start_date",
                ],
            }
        )
        try:
            results = api.search(query).to_dict()["hits"]
        except algolia.AlgoliaSearchAPIError:
            logger.exception("Failed to search the platform for query: %s", query)
            return "search failed"
        else:
            if not results:
                logger.warning("No platform results found for query: %s", query)
                return "no results found"

            response_dict = {}
            for hit in results:
                key = f"{hit['parent_object_title']}: {hit['title']}"
                url = urljoin("https://www.voiio.app", hit["public_url"])
                start_date = hit.get("start_date")
                if start_date:
                    response_dict[key] = f"{url} (Starts: {start_date})"
                else:
                    response_dict[key] = url
            return json.dumps(response_dict)
