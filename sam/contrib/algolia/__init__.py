"""AlgoliaSearch Search API client to perform searches on Algolia."""

import abc

import requests
from algoliasearch.search.client import SearchClientSync

from . import config

__all__ = ["get_client", "AlgoliaSearchAPIError"]


class AlgoliaSearchAPIError(requests.HTTPError):
    pass


class AbstractAlgoliaSearch(abc.ABC):  # pragma: no cover
    @abc.abstractmethod
    def search(self, query):
        return NotImplemented

    @abc.abstractmethod
    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AlgoliaSearch(AbstractAlgoliaSearch):  # pragma: no cover
    def __init__(self, application_id, api_key, index):
        super().__init__()
        self.api_key = api_key
        self.client = SearchClientSync(application_id, api_key)
        self.index_name = index
        self.params = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def search(self, query):
        self.params.update(
            {
                "length": 5,
            }
        )
        try:
            return self.client.search_single_index(
                index_name=self.index_name,
                search_params={"query": query, **self.params},
            )
        except requests.HTTPError as e:
            raise AlgoliaSearchAPIError("The Algolia search API call failed.") from e


class SearchResponseStub:
    def __init__(self):
        self._objects = [
            {
                "title": "Deutschland",
                "parent_object_title": "Ferienangebote",
                "public_url": "https://www.schulferien.org/deutschland/ferien/",
            },
        ]

    def to_dict(self):
        return {"hits": self._objects, "nbPages": 1}


class AlgoliaSearchStub(AbstractAlgoliaSearch):
    def __init__(self):
        self.headers = {}
        self.params = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def search(self, query):
        return SearchResponseStub()


def get_client(index=None) -> AbstractAlgoliaSearch:
    if config.ALGOLIA_SEARCH_API_KEY:  # pragma: no cover
        return AlgoliaSearch(
            application_id=config.ALGOLIA_APPLICATION_ID,
            api_key=config.ALGOLIA_SEARCH_API_KEY,
            index=index or config.ALGOLIA_SEARCH_INDEX,
        )
    else:
        return AlgoliaSearchStub()
