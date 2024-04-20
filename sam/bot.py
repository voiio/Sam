from __future__ import annotations

import json
import logging
from pathlib import Path

import openai

from . import config, tools, utils
from .typing import AUDIO_FORMATS, Roles, RunStatus

logger = logging.getLogger(__name__)


async def complete_run(run_id: str, thread_id: str, *, retry: int = 0, **context):
    """
    Wait for the run to complete.

    Run and submit tool outputs if required.

    Raises:
        RecursionError: If the run status is not "completed" after 10 retries.
        IOError: If the run status is not "completed" or "requires_action".
        ValueError: If the run requires tools but none are provided.
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
            await complete_run(run_id, thread_id, retry=retry + 1, **context)
        case RunStatus.REQUIRES_ACTION:
            await call_tools(run, **context)
            # after we submit the tool outputs, we reset the retry counter
            await complete_run(run_id, thread_id, **context)
        case RunStatus.COMPLETED:
            return
        case _:
            raise IOError(f"Run {run.id} failed with status {run.status}")


async def call_tools(run: openai.types.beta.threads.Run, **context) -> None:
    """
    Call the tools required by the run.

    Raises:
        IOError: If a tool is not found.
        ValueError: If the run does not require any tools.
    """
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    if not (run.required_action and run.required_action.submit_tool_outputs):
        raise ValueError(f"Run {run.id} does not require any tools")
    tool_outputs = []
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        kwargs = json.loads(tool_call.function.arguments)
        try:
            fn = getattr(tools, tool_call.function.name)
        except KeyError as e:
            await client.beta.threads.runs.cancel(
                run_id=run.id, thread_id=run.thread_id
            )
            raise IOError(
                f"Tool {tool_call.function.name} not found, cancelling run {run.id}"
            ) from e
        logger.info("Running tool %s", tool_call.function.name)
        logger.debug("Tool %s arguments: %r", tool_call.function.name, kwargs)
        tool_outputs.append(
            {
                "tool_call_id": tool_call.id,
                "output": fn(**kwargs, _context={**context}),
            }
        )
    logger.info("Submitting tool outputs for run %s", run.id)
    logger.debug("Tool outputs: %r", tool_outputs)
    await client.beta.threads.runs.submit_tool_outputs(
        run.id,  # noqa
        thread_id=run.thread_id,
        tool_outputs=tool_outputs,
    )


async def execute_run(
    assistant_id: str,
    thread_id: str,
    additional_instructions: str = None,
    file_ids: list[str] = None,
    **context,
) -> str:
    """Run the assistant on the OpenAI thread."""
    logger.info(
        "Running assistant %s in thread %s with additional instructions",
        assistant_id,  # noqa
        thread_id,
    )
    logger.debug("Additional instructions: %r", additional_instructions)
    logger.debug("Context: %r", context)
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        additional_instructions=additional_instructions,
        tools=[
            utils.func_to_tool(tools.send_email),
            utils.func_to_tool(tools.web_search),
            utils.func_to_tool(tools.platform_search),
            utils.func_to_tool(tools.fetch_website),
            utils.func_to_tool(tools.fetch_coworker_emails),
            utils.func_to_tool(tools.create_github_issue),
        ],
    )
    try:
        await complete_run(run.id, thread_id, **context)
    except (RecursionError, IOError, ValueError):
        logger.exception("Run %s failed", run.id)
        return "🤯"

    try:
        return await fetch_latest_assistant_message(thread_id)
    except ValueError:
        logger.exception("No assistant message found")
        return "🤯"


async def fetch_latest_assistant_message(thread_id: str) -> str:
    """
    Fetch the latest assistant message from the thread.

    Raises:
        ValueError: If no assistant message is found.
    """
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    messages = await client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages.data:
        if message.role == Roles.ASSISTANT:
            try:
                return await annotate_citations(message.content[0].text)
            except IndexError as e:
                raise ValueError("No assistant message found") from e


async def annotate_citations(
    message_content: openai.types.beta.threads.TextContentBlock,
) -> str:
    """Annotate citations in the text using footnotes and the file metadata."""
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(message_content.annotations):
        message_content.value = message_content.value.replace(
            annotation.text, f" [{index}]"
        )

        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = await client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {file_citation.quote} — {cited_file.filename}")
        elif file_path := getattr(annotation, "file_path", None):
            cited_file = await client.files.retrieve(file_path.file_id)
            citations.append(f"[{index}]({cited_file.filename})")

    # Add footnotes to the end of the message before displaying to user
    message_content.value += "\n" + "\n".join(citations)
    return message_content.value


async def add_message(
    thread_id: str,
    content: str,
    files: [(str, bytes)] = None,
) -> tuple[list[str], bool]:
    """Add a message to the thread."""
    logger.info(f"Adding message to thread={thread_id}")
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    file_ids = []
    voice_prompt = False
    for file_name, file_content in files or []:
        if Path(file_name).suffix.lstrip(".") in AUDIO_FORMATS:
            logger.debug("Transcribing audio file %s", file_name)
            content += (
                "\n"
                + (
                    await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=(file_name, file_content),
                    )
                ).text
            )
            voice_prompt = True
        else:
            logger.debug("Uploading file %s", file_name)
            new_file = await client.files.create(
                file=(file_name, file_content),
                purpose="assistants",
            )
            file_ids.append(new_file.id)
    await client.beta.threads.messages.create(
        thread_id=thread_id,
        content=content,
        role=Roles.USER,
        file_ids=file_ids,
    )
    return file_ids, voice_prompt


async def tts(text: str) -> bytes:
    """Convert text to speech using the OpenAI API."""
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    response = await client.audio.speech.create(
        model=config.TTS_MODEL,
        voice=config.TTS_VOICE,
        input=text,
    )
    return response.read()


async def stt(audio: bytes) -> str:
    """Convert speech to text using the OpenAI API."""
    client: openai.AsyncOpenAI = openai.AsyncOpenAI()
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio,
    )
    return response.text
