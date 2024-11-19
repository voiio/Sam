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
                "attributesToRetrieve": ["title", "parent_object_title", "public_url"],
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
            return json.dumps(
                {
                    f"{hit['parent_object_title']}: {hit['title']}": urljoin(
                        "https://www.voiio.app", hit["public_url"]
                    )
                    for hit in results
                }
            )
