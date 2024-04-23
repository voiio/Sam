from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urljoin

from sam import config
from sam.contrib import algolia
from sam.utils import logger


def search(
    query: str,
    start_date: int = None,
    language: str = None,
    min_age: int = None,
    max_age: int = None,
    _context=None,
) -> str:
    """
    Search the platform for information that matches the given query.

    Args:
        query: The query to search for.
        start_date: The minimum start date in Unix Epoch format (without milliseconds).
        language: The language of the activity, e.g. "DE" or "EN".
        min_age: The minimum age for the activity.
        max_age: The maximum age for the activity.
    """
    filters = "is_published:true"
    if start_date:
        logger.debug("Start date: %s", start_date)
        if datetime.fromtimestamp(start_date, tz=config.TIMEZONE) >= datetime.now(tz=config.TIMEZONE):
            filters += f" AND start_date>{start_date}"
    filters += f" AND end_date>{datetime.now(tz=config.TIMEZONE).timestamp()}"
    logger.debug("Filters: %s", filters)

    if language:
        filters += f" AND languages:{language}"
    if min_age:
        filters += f" AND min_age>={min_age}"
    if max_age:
        filters += f" AND max_age<={max_age}"

    with algolia.get_client() as api:
        logger.warning("Searching the platform for query: %s", query)
        logger.warning("Filters: %s", filters)
        api.params.update(
            {
                "filters": filters,
                "attributesToRetrieve": ["title", "parent_object_title", "public_url"],
            }
        )
        try:
            results = api.search(query)["hits"]
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
