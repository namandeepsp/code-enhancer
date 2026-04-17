import json
import re
from api.models import (
    EnhanceData,
    AlreadyOptimalData,
    CompleteData,
    GenerateData,
    CodeVariant,
    TokenUsage,
    GeneratedLanguageEntry,
)
from api.ai.base import AIResponse


class ParseError(Exception):
    pass


class ResponseParser:
    def _extract_json(self, raw: str) -> dict:
        """Strip markdown fences and parse JSON from AI response."""
        cleaned = raw.strip()

        # Strip ```json ... ``` or ``` ... ``` fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON from AI: {e}")

    def _make_token_usage(self, ai_response: AIResponse) -> TokenUsage:
        return TokenUsage(
            prompt=ai_response.prompt_tokens,
            completion=ai_response.completion_tokens,
            total=ai_response.total_tokens,
        )

    def _parse_variants(self, data: dict) -> list[CodeVariant]:
        variants = data.get("variants", [])
        if not isinstance(variants, list) or len(variants) == 0:
            raise ParseError("Missing or empty variants in AI response")
        return [
            CodeVariant(
                title=v.get("title", ""),
                description=v.get("description", ""),
                code=v.get("code", ""),
            )
            for v in variants
        ]

    def parse_enhance(self, ai_response: AIResponse) -> tuple[bool, EnhanceData | AlreadyOptimalData]:
        data = self._extract_json(ai_response.content)

        if data.get("already_optimal"):
            return True, AlreadyOptimalData(
                message="Your code already follows best practices.",
                notes=data.get("notes", []),
            )

        return False, EnhanceData(
            variants=self._parse_variants(data),
            token_usage=self._make_token_usage(ai_response),
        )

    def parse_complete(self, ai_response: AIResponse) -> tuple[bool, CompleteData | AlreadyOptimalData]:
        data = self._extract_json(ai_response.content)

        if data.get("already_optimal"):
            return True, AlreadyOptimalData(
                message="Your code already follows best practices.",
                notes=data.get("notes", []),
            )

        return False, CompleteData(
            variants=self._parse_variants(data),
            token_usage=self._make_token_usage(ai_response),
        )

    def parse_generate(self, ai_response: AIResponse) -> GenerateData:
        data = self._extract_json(ai_response.content)

        if not isinstance(data, dict) or len(data) == 0:
            raise ParseError("Empty or invalid generate response from AI")

        languages = {}
        for lang, entry in data.items():
            if not isinstance(entry, dict):
                continue
            languages[lang] = GeneratedLanguageEntry(
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                code=entry.get("code", ""),
            )

        if not languages:
            raise ParseError("No valid language entries in generate response")

        return GenerateData(
            languages=languages,
            token_usage=self._make_token_usage(ai_response),
        )
