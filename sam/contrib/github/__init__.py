"""GitHub API client."""

import abc
import os

import requests

__all__ = ["get_client", "GitHubAPIError"]


class GitHubAPIError(requests.HTTPError):
    pass


class AbstractGitHubAPIWrapper(abc.ABC):  # pragma: no cover
    @abc.abstractmethod
    def create_issue(self, title, body):
        return NotImplemented

    @abc.abstractmethod
    def __enter__(self):
        return NotImplemented

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        return NotImplemented


class GitHubAPIWrapper(requests.Session, AbstractGitHubAPIWrapper):  # pragma: no cover
    endpoint = "https://api.github.com"

    def __init__(self, token):
        super().__init__()
        self.token = token
        self.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def create_issue(self, title, body):
        response = self.post(
            f"{self.endpoint}/repos/{os.getenv('GITHUB_ORG')}/{os.getenv('GITHUB_REPOSITORY')}/issues",
            json={"title": title, "body": body},
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise GitHubAPIError("The GitHub API call failed.") from e
        return response.json()


class GitHubAPIWrapperStub(AbstractGitHubAPIWrapper):
    def __init__(self):
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def create_issue(self, title, body):
        return {
            "title": title,
            "body": body,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        }


def get_client():
    if token := os.getenv("GITHUB_TOKEN"):
        return GitHubAPIWrapper(token=token)
    return GitHubAPIWrapperStub()
