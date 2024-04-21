import logging

from . import GitHubAPIError, config, get_client

logger = logging.getLogger(__name__)


def create_github_issue(
    title: str, body: str, repo: config.GITHUB_REPOS, _context=None
) -> str:
    """
    Create an issue on GitHub with the given title and body.

    A good issues usually includes a user story for a feature,
    or a step by step guide how to reproduce a bug.

    You should provide ideas for a potential solution,
    including code snippet examples in a Markdown code block.

    Args:
        title: The title of the issue.
        body: The body of the issue, markdown supported.
        repo: The repository to create the issue in.
    """
    if repo not in config.GITHUB_REPOS.__members__:
        logger.warning("Invalid repo: %s", repo)
        return "invalid repo"
    with get_client() as api:
        try:
            response = api.create_issue(title, body, repo)
        except GitHubAPIError:
            logger.exception("Failed to create issue on GitHub")
            return "failed to create issue"
        else:
            return response["html_url"]
