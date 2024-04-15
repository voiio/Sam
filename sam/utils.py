import datetime
import enum
import inspect
import json
import logging
import os
import re
import smtplib
import ssl
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import openai
import redis
import requests
import yaml
from bs4 import ParserRejectedMarkup
from markdownify import markdownify as md

from . import config
from .contrib import brave

logger = logging.getLogger(__name__)

__all__ = ["get_thread_id", "storage", "func_to_tool", "send_email"]

storage: redis.Redis = redis.from_url(config.REDIS_URL)

type_map = {
    str: "string",
    int: "integer",
    float: "number",
    list: "array",
    dict: "object",
    enum.StrEnum: "string",
    enum.IntEnum: "integer",
}


def func_to_tool(fn: callable) -> dict:
    signature: inspect.Signature = inspect.signature(fn)
    description, args = fn.__doc__.split("Args:")
    doc_data = yaml.safe_load(args.split("Returns:")[0])
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": "\n".join(
                filter(None, (line.strip() for line in description.splitlines()))
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": type_map[param.annotation],
                        "description": doc_data[param.name],
                    }
                    for param in signature.parameters.values()
                },
                "required": [
                    param.name
                    for param in signature.parameters.values()
                    if param.default is inspect.Parameter.empty
                ],
            },
        },
    }


def get_thread_id(slack_id) -> str:
    """
    Get the thread from the user_id or channel.

    Args:
        slack_id: The user or channel id.

    Returns:
        The thread id.
    """
    thread_id = storage.get(slack_id)
    if thread_id:
        thread_id = thread_id.decode()
    else:
        thread_id = openai.beta.threads.create().id

    midnight = datetime.datetime.combine(
        datetime.date.today(), datetime.time.max, tzinfo=config.TIMEZONE
    )

    storage.set(slack_id, thread_id, exat=int(midnight.timestamp()))

    return thread_id


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
    with smtplib.SMTP(url.hostname, url.port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(url.username, url.password)
        msg = MIMEMultipart()
        msg["From"] = f"Sam <{from_email}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        server.sendmail(from_email, [to], msg.as_string())

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
