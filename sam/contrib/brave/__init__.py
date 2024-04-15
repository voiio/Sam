"""Brave Search API client to perform web searches."""

import abc
import os

import requests

__all__ = ["get_client", "BraveSearchAPIError"]


class BraveSearchAPIError(requests.HTTPError):
    pass


class AbstractBraveSearchAPIWrapper(abc.ABC):  # pragma: no cover

    @abc.abstractmethod
    def search(self, query):
        return NotImplemented

    @abc.abstractmethod
    def __enter__(self):
        return NotImplemented

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        return NotImplemented


class BraveSearchAPIWrapper(
    requests.Session, AbstractBraveSearchAPIWrapper
):  # pragma: no cover
    endpoint = "https://api.search.brave.com/res/v1"

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.compression = True
        self.headers.update(
            {
                "X-Subscription-Token": self.api_key,
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
            }
        )

    def search(self, query):
        response = self.get(f"{self.endpoint}/web/search", params={"q": query})
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise BraveSearchAPIError("The brave search API call failed.") from e
        return response.json()


class BraveSearchAPIWrapperStub(AbstractBraveSearchAPIWrapper):
    def __init__(self):
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def search(self, query):
        match query:
            case "ferien":
                return {
                    "mixed": {
                        "main": [
                            {"all": False, "index": 0, "type": "web"},
                        ],
                        "side": [],
                        "top": [],
                        "type": "mixed",
                    },
                    "query": {
                        "bad_results": False,
                        "city": "",
                        "country": "us",
                        "header_country": "",
                        "is_navigational": False,
                        "is_news_breaking": False,
                        "local_decision": "drop",
                        "local_locations_idx": 0,
                        "more_results_available": True,
                        "original": "ferien in deutschland",
                        "postal_code": "",
                        "should_fallback": False,
                        "show_strict_warning": False,
                        "spellcheck_off": True,
                        "state": "",
                    },
                    "type": "search",
                    "web": {
                        "family_friendly": True,
                        "results": [
                            {
                                "description": "Aktuelle Schulferien "
                                "<strong>Deutschland</strong> 2024. Alle "
                                "Ferientermine für "
                                "<strong>Deutschland</strong> 2024 "
                                "sorgfältig recherchiert und tabellarisch "
                                "dargestellt. <strong>Ferien</strong> "
                                "<strong>Deutschland</strong>.",
                                "family_friendly": True,
                                "is_source_both": False,
                                "is_source_local": False,
                                "language": "de",
                                "meta_url": {
                                    "favicon": "https://imgs.search.brave.com/ZLqgQhJm8PmXPMZxCsF6bE1k7bIeU-E7r6lzgu-4CP8/rs:fit:32:32:1/g:ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvZWQyZjczMDIy/ZDIxN2UzZWY1ODdm/ZDU2YTYxNWZlNmE0/MTM1YWU4ODM1ZTMx/N2EzN2FiZDA4Yjkw/MDBlODM3NS93d3cu/c2NodWxmZXJpZW4u/b3JnLw",
                                    "hostname": "www.schulferien.org",
                                    "netloc": "schulferien.org",
                                    "path": "  › ferien deutschland",
                                    "scheme": "https",
                                },
                                "profile": {
                                    "img": "https://imgs.search.brave.com/ZLqgQhJm8PmXPMZxCsF6bE1k7bIeU-E7r6lzgu-4CP8/rs:fit:32:32:1/g:ce/aHR0cDovL2Zhdmlj/b25zLnNlYXJjaC5i/cmF2ZS5jb20vaWNv/bnMvZWQyZjczMDIy/ZDIxN2UzZWY1ODdm/ZDU2YTYxNWZlNmE0/MTM1YWU4ODM1ZTMx/N2EzN2FiZDA4Yjkw/MDBlODM3NS93d3cu/c2NodWxmZXJpZW4u/b3JnLw",
                                    "long_name": "schulferien.org",
                                    "name": "Schulferien",
                                    "url": "https://www.schulferien.org/deutschland/ferien/",
                                },
                                "subtype": "generic",
                                "title": "Ferien Deutschland",
                                "type": "search_result",
                                "url": "https://www.schulferien.org/deutschland/ferien/",
                            },
                        ],
                        "type": "search",
                    },
                }

            case "error":
                raise BraveSearchAPIError("The brave search API call failed.")
        return {
            "mixed": {
                "main": [
                    {"all": False, "index": 0, "type": "web"},
                ],
                "side": [],
                "top": [],
                "type": "mixed",
            },
            "query": {
                "bad_results": False,
                "city": "",
                "country": "us",
                "header_country": "",
                "is_navigational": False,
                "is_news_breaking": False,
                "local_decision": "drop",
                "local_locations_idx": 0,
                "more_results_available": True,
                "original": "ferien in deutschland",
                "postal_code": "",
                "should_fallback": False,
                "show_strict_warning": False,
                "spellcheck_off": True,
                "state": "",
            },
            "type": "search",
            "web": {
                "family_friendly": True,
                "results": [],
                "type": "search",
            },
        }


def get_client() -> AbstractBraveSearchAPIWrapper:
    if api_key := os.getenv("BRAVE_SEARCH_API_KEY"):  # pragma: no cover
        return BraveSearchAPIWrapper(api_key=api_key)
    return BraveSearchAPIWrapperStub()
