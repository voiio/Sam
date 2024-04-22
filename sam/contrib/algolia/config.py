# The Algolia search API key.
import os

#: The algolia API key.
ALGOLIA_SEARCH_API_KEY: str = os.getenv("ALGOLIA_SEARCH_API_KEY")
#: The Algolia application ID.
ALGOLIA_APPLICATION_ID: str = os.getenv("ALGOLIA_APPLICATION_ID")
#: The Algolia search index.
ALGOLIA_SEARCH_INDEX: str = os.getenv("ALGOLIA_SEARCH_INDEX")
