import asyncio
import logging
import os
import sys

import click
import openai
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration

from . import config

sentry_sdk.init(
    dsn=config.SENTRY_DSN,
    enable_tracing=True,
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


@cli.group(chain=True)
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
def assistants(verbose):
    """Manage OpenAI assistants."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(
        handlers=[handler], level=logging.DEBUG if verbose else logging.INFO
    )


@assistants.command(name="list")
def _list():
    """List all assistants configured in your project."""
    assistant_list = list(config.load_assistants())
    for assistant_config in assistant_list:
        click.echo(
            f"{assistant_config.name} ({assistant_config.project}): {assistant_config.assistant_id}"
        )
    if not assistant_list:
        click.echo("No assistants configured.")


@assistants.command()
def upload():
    """Compile and upload all assistants system prompts to OpenAI."""
    assistant_list = list(config.load_assistants())
    for assistant_config in assistant_list:
        click.echo(f"Uploading {assistant_config.name}...", nl=False)
        project_api_key_name = (
            f"OPENAI_{assistant_config.project.replace('-', '_').upper()}_API_KEY"
        )
        project_api_key = os.getenv(project_api_key_name)
        with openai.OpenAI(api_key=project_api_key) as client:
            client.beta.assistants.update(
                assistant_id=assistant_config.assistant_id,
                instructions=assistant_config.system_prompt,
            )
            click.echo(" Done!")
    if not assistant_list:
        click.echo("No assistants configured.")


if __name__ == "__main__":
    cli()
