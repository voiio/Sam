import json
import logging

import openai

from . import tools, utils
from .typing import Roles, RunStatus

logger = logging.getLogger(__name__)


async def complete_run(run_id: str, thread_id: str, retry: int = 0):
    """
    Wait for the run to complete.

    Run and submit tool outputs if required.

    Raises:
        RecursionError: If the run status is not "completed" after 10 retries.
    """
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    if retry > 10:
        await client.beta.threads.runs.cancel(run_id=run_id, thread_id=thread_id)
        raise RecursionError("Max retries exceeded")
    run = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    logger.info("Run %s status: %s", run.id, run.status)  # noqa
    match run.status:
        case status if status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS]:
            await utils.backoff(retry)
            await complete_run(run_id, thread_id, retry=retry + 1)
        case RunStatus.REQUIRES_ACTION:
            if (
                run.required_action
                and run.required_action.submit_tool_outputs
                and run.required_action.submit_tool_outputs.tool_calls
            ):
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    kwargs = json.loads(tool_call.function.arguments)
                    try:
                        fn = getattr(tools, tool_call.function.name)
                    except KeyError:
                        logger.exception(
                            "Tool %s not found, cancelling run %s",
                            tool_call.function.name,
                            run_id,
                        )
                        await client.beta.threads.runs.cancel(
                            run_id=run_id, thread_id=thread_id
                        )
                    tool_outputs.append(
                        {
                            "tool_call_id": tool_call.id,  # noqa
                            "output": await fn(**kwargs),
                        }
                    )

                await client.beta.threads.runs.submit_tool_outputs(
                    run.id,  # noqa
                    thread_id=thread_id,
                    tool_outputs=tool_outputs,
                )
            await complete_run(run_id, thread_id)  # we reset the retry counter


async def run(
    assistant_id: str, thread_id: str, additional_instructions: str = None
) -> str:
    """Run the assistant on the OpenAI thread."""
    logger.info(
        "Running assistant %s in thread %s with additional instructions: %s",
        assistant_id,  # noqa
        thread_id,
        additional_instructions,
    )
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    _run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        additional_instructions=additional_instructions,
        tools=[
            utils.func_to_tool(tools.send_email),
            utils.func_to_tool(tools.web_search),
            utils.func_to_tool(tools.fetch_website),
        ],
    )
    await complete_run(_run.id, thread_id)

    messages = await client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages.data:
        if message.role == Roles.ASSISTANT:
            message_content = message.content[0].text

            annotations = message_content.annotations
            citations = []

            # Iterate over the annotations and add footnotes
            for index, annotation in enumerate(annotations):
                message_content.value = message_content.value.replace(
                    annotation.text, f" [{index}]"
                )

                if file_citation := getattr(annotation, "file_citation", None):
                    cited_file = client.files.retrieve(file_citation.file_id)
                    citations.append(
                        f"[{index}] {file_citation.quote} — {cited_file.filename}"
                    )
                elif file_path := getattr(annotation, "file_path", None):
                    cited_file = client.files.retrieve(file_path.file_id)
                    citations.append(f"[{index}]({cited_file.filename})")

            # Add footnotes to the end of the message before displaying to user
            message_content.value += "\n" + "\n".join(citations)

            return message_content