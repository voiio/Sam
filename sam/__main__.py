import asyncio
import logging
import sys

import click
import sentry_sdk

from . import config

sentry_sdk.init(config.SENTRY_DSN)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
def cli(verbose):
    """Sam – cuz your company is nothing with Sam."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("sam")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)


@cli.group(chain=True)
def run():
    """Run an assistent bot, currently only Slack is supported."""


@run.command()
def slack():
    """Run the Slack bot demon."""
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

    from .slack import app

    loop = asyncio.get_event_loop()

    loop.run_until_complete(
        AsyncSocketModeHandler(app, config.SLACK_APP_TOKEN).start_async()
    )


if __name__ == "__main__":
    cli()
