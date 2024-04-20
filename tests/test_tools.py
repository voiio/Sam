import json
import smtplib
from unittest import mock

import pytest
import requests

from sam import tools
from sam.contrib import algolia


@pytest.fixture
def smtp(monkeypatch):
    smtp_fn = mock.MagicMock()
    smtp = mock.MagicMock()
    smtp_fn.__enter__.return_value = smtp
    monkeypatch.setattr("smtplib.SMTP", mock.Mock(return_value=smtp_fn))
    return smtp


def test_send_email(smtp):
    assert (
        tools.send_email("sam@openai.com", "subject", "body")
        == "Email sent successfully!"
    )
    assert smtp.sendmail.called
    assert smtp.sendmail.call_args[0][0] == "sam@voiio.de"


def test_send_email__ioerror(smtp):
    smtp.sendmail.side_effect = smtplib.SMTPException
    assert (
        tools.send_email("sam@openai.com", "subject", "body")
        == "Email not sent. An error occurred."
    )


def test_web_search():
    assert (
        tools.web_search("ferien")
        == '{"Ferien Deutschland": "https://www.schulferien.org/deutschland/ferien/"}'
    )
    assert tools.web_search("does not exist") == "no results found"
    assert tools.web_search("error") == "search failed"


def test_web_search__with_coordinates():
    assert (
        tools.web_search("ferien")
        == '{"Ferien Deutschland": "https://www.schulferien.org/deutschland/ferien/"}'
    )


def test_create_github_issue():
    assert (
        tools.create_github_issue("title", "body", "voiio/sam")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_create_github_issue__invalid_repo():
    assert tools.create_github_issue("title", "body", "not-valid") == "invalid repo"


def test_platform_search():
    assert tools.platform_search("ferien") == json.dumps(
        {
            "Ferienangebote: Deutschland": "https://www.schulferien.org/deutschland/ferien/"
        }
    )


def test_platform_search_with_error():
    with mock.patch(
        "sam.contrib.algolia.AlgoliaSearchStub.search",
        side_effect=algolia.AlgoliaSearchAPIError,
    ):
        assert tools.platform_search("something") == "search failed"


def test_platform_search_no_results():
    with mock.patch(
        "sam.contrib.algolia.AlgoliaSearchStub.search", return_value={"hits": []}
    ):
        assert tools.platform_search("something") == "no results found"
