import smtplib
from unittest import mock

import pytest

from sam import tools


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
