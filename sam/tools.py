from __future__ import annotations

import re
import smtplib
import ssl
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from markdownify import markdownify as md

from sam import config
from sam.utils import logger


def send_email(to: str, subject: str, body: str, _context=None):
    """
    Send an email the given recipients. The user is always cc'd on the email.

    Args:
        to: Comma separated list of email addresses.
        subject: The subject of the email.
        body: The body of the email.
    """
    _context = _context or {}

    from_email = config.FROM_EMAIL
    if config.EMAIL_WHITELIST_PATTERN and not config.EMAIL_WHITELIST_PATTERN.match(to):
        return "Email not sent. The recipient is not in the whitelist."
    urllib.parse.uses_netloc.append("smtps")
    url = urllib.parse.urlparse(config.EMAIL_URL)
    context = ssl.create_default_context()
    msg = MIMEMultipart()
    msg["From"] = f"Sam <{from_email}>"
    msg["To"] = to
    to_addr = to.split(",")
    if cc := _context.get("email"):
        msg["Cc"] = cc
        to_addr.append(cc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(url.hostname, url.port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(url.username, url.password)
            server.sendmail(from_email, to_addr, msg.as_string())
    except smtplib.SMTPException:
        logger.exception("Failed to send email to: %s", to)
        return "Email not sent. An error occurred."

    return "Email sent successfully!"


def fetch_website(url: str, _context=None) -> str:
    """
    Fetch the website for the given URL and return the content as Markdown.

    You MUST NOT use this function twice if there was an error fetching the website.

    Args:
        url: The URL of the website to fetch.
    """
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        logger.exception("Failed to fetch website: %s", url)
        return "invalid url"
    else:
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.exception("Failed to fetch website: %s", url)
            return "website returned an error"
        else:
            return re.sub(
                r" {2,}", " ", re.sub(r"\n\s+", "\n", md(response.text))
            ).strip()
