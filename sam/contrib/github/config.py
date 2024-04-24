import enum
import os

#: GitHub token to access the GitHub API.
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN")

#: CSV of GitHub repositories the bot can access.
GITHUB_REPOS: type[enum.Enum] = enum.StrEnum(
    "GITHUB_REPOS",
    {repo: repo for repo in os.getenv("GITHUB_REPOS", "").split(",") if repo},
)
