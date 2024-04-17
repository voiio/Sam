from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import ParserRejectedMarkup
from markdownify import markdownify as md
from slack_bolt import App

from sam import config
from sam.contrib import brave
from sam.utils import logger


def send_email(to: str, subject: str, body: str):
    """
    Write and send email.

    Args:
        to: The recipient of the email, e.g. john.doe@voiio.de.
        subject: The subject of the email.
        body: The body of the email.
    """
    email_url = os.getenv("EMAIL_URL")
    from_email = os.getenv("FROM_EMAIL", "sam@voiio.de")
    email_white_list = os.getenv("EMAIL_WHITE_LIST")
    if email_white_list and not re.match(email_white_list, to):
        return "Email not sent. The recipient is not in the whitelist."
    urllib.parse.uses_netloc.append("smtps")
    url = urllib.parse.urlparse(email_url)
    context = ssl.create_default_context()
    msg = MIMEMultipart()
    msg["From"] = f"Sam <{from_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(url.hostname, url.port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(url.username, url.password)
            server.sendmail(from_email, [to], msg.as_string())
    except smtplib.SMTPException:
        logger.exception("Failed to send email to: %s", to)
        return "Email not sent. An error occurred."

    return "Email sent successfully!"


def web_search(query: str) -> str:
    """
    Search the internet for information that matches the given query.

    The search is location aware and will return results based on the user's location.

    Args:
        query: The query to search for.
    """
    with brave.get_client() as api:
        if config.BRAVE_SEARCH_LATITUDE and config.BRAVE_SEARCH_LONGITUDE:
            api.headers.update(
                {
                    "X-Loc-Lat": config.BRAVE_SEARCH_LATITUDE,
                    "X-Loc-Long": config.BRAVE_SEARCH_LONGITUDE,
                }
            )
        try:
            results = api.search(query)["web"]
        except brave.BraveSearchAPIError:
            logger.exception("Failed to search the web for query: %s", query)
            return "search failed"
        else:
            if not results["results"]:
                logger.warning("No results found for query: %s", query)
                return "no results found"
            return json.dumps(
                {result["title"]: result["url"] for result in results["results"]}
            )


def fetch_website(url: str) -> str:
    """
    Fetch the website for the given URL and return the content as Markdown.

    Args:
        url: The URL of the website to fetch.
    """
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        logger.exception("Failed to fetch website: %s", url)
        return "failed to fetch website"
    else:
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.exception("Failed to fetch website: %s", url)
            return "failed to fetch website"
        else:
            try:
                return md(response.text)
            except ParserRejectedMarkup:
                return "failed to parse website"


def fetch_slack_user_emails() -> str:
    """
    Fetch the emails of the Slack users.

    Args: None

    Returns: A dictionary of user slack IDs and their emails set on slack.
    """
    app = App(token=config.SLACK_BOT_TOKEN)
    try:
        response = app.client.users_list()
        return json.dumps(
            {
                user["id"]: user.get("profile", {}).get("email")
                for user in response["members"]
                if "email" in user.get("profile", {})
            }
        )
    except Exception as e:
        return f"an error occurred: {e}"
