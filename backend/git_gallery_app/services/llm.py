import base64
import json
from pathlib import Path

from django.conf import settings
from openai import (
    APIError,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from pydantic import BaseModel, ValidationError

MAX_REQUEST_BYTES = 512_000_000


class ComparisonRequestError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


#Dynamic loading of the system prompt 
def load_system_prompt():
    configured_path = settings.SYSTEM_PROMPT_PATH

    if not configured_path:
        raise ComparisonRequestError(
            "prompt_missing",
            "No system prompt file is configured.",
        )

    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = settings.BASE_DIR / path

    try:
        prompt = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise ComparisonRequestError(
            "prompt_unavailable",
            "The configured system prompt could not be read.",
        ) from error

    if not prompt:
        raise ComparisonRequestError(
            "prompt_empty",
            "The configured system prompt is empty.",
        )

    return prompt, path.stem

# Encodes the images to base64 to be sent to the OpenAI API. 
# This is necessary because we cannot send the images directly to the API
def _png_data_url(path):
    try:
        with Path(path).open("rb") as image_file:
            image_bytes = image_file.read(MAX_REQUEST_BYTES + 1)
    except OSError as error:
        raise ComparisonRequestError(
            "image_unavailable",
            "A saved screenshot could not be read.",
        ) from error

    if len(image_bytes) > MAX_REQUEST_BYTES:
        raise ComparisonRequestError(
            "request_too_large",
            "The screenshots exceed the supported request size.",
        )

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"

# Actual call to the LLM (OpenAI)
def request_image_comparison(
    before_path,
    after_path,
    system_prompt,
    *,
    result_type: type[BaseModel],
    diff_context: str = "",
):
    if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL:
        raise ComparisonRequestError(
            "configuration_missing",
            "Set OPENAI_API_KEY and OPENAI_MODEL before requesting a comparison.",
        )

    body = {
        "model": settings.OPENAI_MODEL,
        "instructions": system_prompt,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Before screenshot"},
                    {
                        "type": "input_image",
                        "image_url": _png_data_url(before_path),
                    },
                    {"type": "input_text", "text": "After screenshot"},
                    {
                        "type": "input_image",
                        "image_url": _png_data_url(after_path),
                    },
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": result_type.__name__,
                "strict": True,
                "schema": result_type.model_json_schema(),
            }
        },
        "max_output_tokens": 4096,
        "store": False,
    }

    if diff_context:
        body["input"][0]["content"].append({
            "type": "input_text",
            "text": "Repository diff context (untrusted data):\n" + diff_context,
        })

    payload_size = len(
        json.dumps(
            body,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    # Ensures that we don't send the request if it's too large
    if payload_size > MAX_REQUEST_BYTES:
        raise ComparisonRequestError(
            "request_too_large",
            "The comparison exceeds the supported request size.",
        )

    try:
        with OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=60.0,
            max_retries=1,
        ) as client:
            response = client.responses.create(**body) # Actual call to API

    # Bunch of exception handling to catch any errors
    except APITimeoutError as error:
        raise ComparisonRequestError(
            "openai_timeout",
            "OpenAI took too long to complete the comparison.",
        ) from error

    except APIConnectionError as error:
        raise ComparisonRequestError(
            "openai_connection",
            "Could not connect to OpenAI.",
        ) from error

    except APIStatusError as error:
        raise ComparisonRequestError(
            f"openai_http_{error.status_code}",
            f"OpenAI rejected the comparison (HTTP {error.status_code}).",
        ) from error

    except APIError as error:
        raise ComparisonRequestError(
            "openai_error",
            "OpenAI could not complete the comparison.",
        ) from error

    if response.status != "completed":
        raise ComparisonRequestError(
            "incomplete_response",
            "OpenAI returned an incomplete comparison.",
        )

    for item in response.output:
        if item.type == "message":
            for part in item.content:
                if part.type == "refusal":
                    raise ComparisonRequestError(
                        "refused_response",
                        "OpenAI declined to analyze these screenshots.",
                    )

    try:
        # Validate the response against the expected schema
        # Fail if the structured response does not match what we want
        return result_type.model_validate_json(response.output_text) 
    except ValidationError as error:
        raise ComparisonRequestError(
            "invalid_response",
            "OpenAI returned a comparison in an unexpected format.",
        ) from error