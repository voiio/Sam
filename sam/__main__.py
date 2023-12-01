import logging
import sys

import click
from slack_bolt.adapter.socket_mode import SocketModeHandler

from . import config


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
def cli(verbose):
    """Sam – cuz your company is nothing with Sam."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(clientip)-15s %(message)s"))
    handler.setLevel("INFO")
    level = logging.WARNING
    if verbose:
        level = logging.INFO
    logging.basicConfig(level=level, handlers=[handler])


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
