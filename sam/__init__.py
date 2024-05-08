"""
A GPT-based Slack bot trained to specific personalities and use cases.

Sam uses OpenAI's assistant API to align ChatGPT to a specific personality traits,
provide domain-specific knowledge and context to provide a work-colleague like
experience.
"""

from . import _version, bot, typing, utils

__version__ = _version.version
VERSION = _version.version_tuple


__all__ = ["__version__", "VERSION", "typing", "utils", "bot"]
