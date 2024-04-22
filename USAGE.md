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

## Training CLI

The training CLI is used to "train" the OpenAI assistant. You can upload
the system prompts to OpenAI to align the assistant with your company's
specific needs.

```bash
❯ sam assistants --help
Usage: sam assistants [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Manage OpenAI assistants.

Options:
  -v, --verbose  Enables verbose mode.
  --help         Show this message and exit.

Commands:
  list    List all assistants configured in your project.
  upload  Compile and upload all assistants system prompts to OpenAI.
```

To upload the system prompts to OpenAI you can run:

```commandline
sam assistants upload
```

### System Prompts

You can configure assistants in your `pyproject.toml` file.

```toml
# pyproject.toml
[[tool.prompts.assistants]]
name = "Sam"
assistant_id = "asst_1234567890"
project = "default-project"
instructions = [
  "assistants/sam.md",
  "assistants/shared/values.md",
  "assistants/shared/principles.md",
  "assistants/shared/style.md",
]
```

The `instructions` field is a list of markdown files that contain the system prompts.
You will need to set they OpenAI secret key in the environment variable.
