from openai import OpenAI

__all__ = ["get_client"]


def get_client():
    return OpenAI()
