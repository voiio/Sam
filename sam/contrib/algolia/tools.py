from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urljoin

from sam import config
from sam.contrib import algolia
from sam.utils import logger


def search(
    query: str,
    start_date: str = None,
    language: str = None,
    min_age: int = None,
    max_age: int = None,
    _context=None,
) -> str:
    """
    Search the platform for information that matches the given query.

    Translate the query into a German language.
    Make sure the dates are in 2024 and in POSIX timestamp format.

    Args:
        query: The query to search for (should be translated into German).
        start_date: The minimum start date for the activity in POSIX timestamp.
        language: The language of the activity, e.g. "DE" or "EN".
        min_age: The minimum age for the activity.
        max_age: The maximum age for the activity.
    """
    filters = "is_published:true"
    if start_date:
        start_date = datetime.fromtimestamp(int(start_date), tz=config.TIMEZONE)
        start_date = start_date.replace(year=2024).timestamp()

        logger.warning("Start date: %s", start_date)
        filters += f" AND start_date>{start_date}"
    filters += f" AND end_date>{datetime.now(tz=config.TIMEZONE).timestamp()}"

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
