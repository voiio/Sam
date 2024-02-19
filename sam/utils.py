import enum
import functools
import inspect
import os
import re
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import openai
import redis
import yaml

from . import config

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


@functools.lru_cache
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

    storage.set(slack_id, thread_id)

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
    from_email = os.getenv("FROM_EMAIL")
    email_white_list = os.getenv("EMAIL_WHITE_LIST")
    if email_white_list and not re.match(email_white_list, to):
        return "Email not sent. The recipient is not in the whitelist."
    urllib.parse.uses_netloc.append("smtps")
    url = urllib.parse.urlparse(email_url)
    with smtplib.SMTP_SSL(url.hostname, url.port) as server:
        server.login(url.username, url.password)
        msg = MIMEMultipart()
        msg["From"] = url.username
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        server.sendmail(from_email, to, msg.as_string())

    return "Email sent successfully!"
