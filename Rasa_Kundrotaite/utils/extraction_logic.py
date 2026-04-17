from models import ObligationList
from huggingface_hub import InferenceClient
import json
import logging
from json import JSONDecodeError
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)
client = InferenceClient()

_SYSTEM_PROMPT = """Extract only binding legal obligations from the following text.

An obligation is a sentence where a specific actor is REQUIRED or PROHIBITED from doing something, expressed using a strong deontic modal: "shall", "must", "is required to", "is obliged to", "may not", "must not", "shall not".

Do NOT extract:
- Aspirational or policy goals ("should", "ought to", "aims to", "is encouraged to", "strives to")
- Definitions or recitals
- Descriptions of purpose or context
- Recommendations or best practices

For each obligation return a JSON object with key "obligations" containing an array of objects, each with:
- "actor": the specific entity that is obligated (e.g. "Member States", "the provider", "the Commission")
- "action": what they are required or prohibited from doing
- "modality": the exact modal expression used (e.g. "shall", "must not", "is required to")
- "condition": any triggering or temporal condition (or empty string)
- "span": the verbatim sentence from the text
- "rationale": one sentence explaining why this qualifies as a binding obligation (or empty string)

Return only the JSON object, no additional text."""


def get_default_prompt() -> str:
    return _SYSTEM_PROMPT


def _strip_code_fence(text: str) -> str:
    if "```" not in text:
        return text
    inner = text.split("```")[1]
    if inner.startswith("json"):
        inner = inner[4:]
    return inner.strip()


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _call_api(chunk: str) -> str:
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": get_default_prompt()},
            {
                "role": "user",
                "content": f"Extract all obligations from this text:\n\n{chunk}",
            },
        ],
    )
    return completion.choices[0].message.content.strip()


def extract_obligations(chunk: str) -> list[dict]:
    text = _call_api(chunk)
    text = _strip_code_fence(text)

    try:
        data = json.loads(text)
        result = ObligationList(**data)
        return [o.model_dump() for o in result.obligations]
    except (JSONDecodeError, ValidationError) as e:
        logger.error("Failed to parse model response: %s\nRaw: %s", e, text)
        raise ValueError(f"Model returned unparseable response: {e}") from e
