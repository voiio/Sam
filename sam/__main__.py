import logging
import sys

import click
from slack_bolt.adapter.socket_mode import SocketModeHandler

from . import config


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
    from .slack import app

    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()


if __name__ == "__main__":
    cli()
