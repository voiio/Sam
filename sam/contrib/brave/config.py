# Brave Search API client to perform web searches.
import os

BRAVE_SEARCH_API_KEY: str | None = os.getenv("BRAVE_SEARCH_API_KEY")
#: The longitude of the bot's location for Brave Search.
BRAVE_SEARCH_LONGITUDE: float | None = (
    float(os.getenv("BRAVE_SEARCH_LONGITUDE"))
    if "BRAVE_SEARCH_LONGITUDE" in os.environ
    else None
)
#: The latitude of the bot's location for Brave Search.
BRAVE_SEARCH_LATITUDE: float | None = (
    float(os.getenv("BRAVE_SEARCH_LATITUDE"))
    if "BRAVE_SEARCH_LATITUDE" in os.environ
    else None
)
