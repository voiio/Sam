import asyncio
import logging
import sys

import click
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration

from . import config

sentry_sdk.init(
    dsn=config.SENTRY_DSN,
    traces_sample_rate=0.05,
    integrations=[
        AsyncioIntegration(),
    ],
)


@click.group()
def cli():
    """Sam – cuz your company is nothing with Sam."""


@cli.group(chain=True)
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
def run(verbose):
    """Run an assistent bot."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)7s %(name)s - %(message)s")
    )
    logging.basicConfig(
        handlers=[handler], level=logging.DEBUG if verbose else logging.INFO
    )


@run.command()
def slack():
    """Run the Slack bot demon."""
    from .slack import run_slack

    asyncio.run(run_slack())


if __name__ == "__main__":
    cli()
