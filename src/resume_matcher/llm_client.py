"""Instructor-wrapped Anthropic client."""

import anthropic
import instructor

from resume_matcher.config import get_api_key


def get_client() -> instructor.Instructor:
    """Return an Instructor-patched Anthropic client.

    Instructor wraps the Anthropic client so that API responses are
    automatically validated against Pydantic models. If validation fails,
    Instructor retries the request with the validation error fed back to
    the model so it can self-correct.
    """
    api_key = get_api_key()  # raises ConfigError if dummy/missing
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    return instructor.from_anthropic(anthropic_client)
