# Usage

## Bot CLI

The bot CLI is the main entry point for running the bot.
It provides a few commands to run the bot in different environments
and to increase the verbosity of the logs.

```bash
❯ sam run --help
Usage: sam run [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Run an assistent bot.

Options:
  -v, --verbose  Enables verbose mode.
  --help         Show this message and exit.

Commands:
  slack  Run the Slack bot demon.
```

To run the Slack bot all you need is to run:

```commandline
sam run slack
```
