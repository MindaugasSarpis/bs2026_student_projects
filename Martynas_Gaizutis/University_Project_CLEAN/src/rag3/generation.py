from __future__ import annotations

import logging

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

from rag3.config import AppConfig

logger = logging.getLogger(__name__)


class GenerativeReader:
    def __init__(self, config: AppConfig):
        self.config = config
        self.settings = config.generative_reader

        if not config.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your environment or .env file before running generation."
            )

        self.client = OpenAI(api_key=config.api_key)

    def _create_prompt(self, context: str, question: str) -> str:
        return self.settings.default_prompt.format(context=context, question=question)

    @staticmethod
    def _truncate_context(context: str, max_tokens: int) -> str:
        words = context.split()
        if len(words) <= max_tokens:
            return context
        logger.warning("Context too long (%s words). Truncating to %s.", len(words), max_tokens)
        return " ".join(words[:max_tokens])

    def generate_answer(self, question: str, context: str, max_tokens: int | None = None) -> str:
        response_tokens = max_tokens or self.settings.max_tokens
        prompt = self._create_prompt(
            context=self._truncate_context(context, max_tokens=6000),
            question=question,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a careful assistant that answers based on supplied context.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=response_tokens,
                temperature=self.settings.temperature,
                top_p=self.settings.top_p,
                frequency_penalty=self.settings.frequency_penalty,
                presence_penalty=self.settings.presence_penalty,
            )
            return (response.choices[0].message.content or "").strip()
        except APIConnectionError:
            return "OpenAI API is unreachable right now."
        except RateLimitError:
            return "OpenAI rate limit hit. Please retry in a moment."
        except APIStatusError as exc:
            logger.error("OpenAI API status error: %s", exc)
            return "OpenAI API returned an unexpected status."
        except Exception as exc:
            logger.exception("Generation failed: %s", exc)
            return "Answer generation failed due to an unexpected error."
