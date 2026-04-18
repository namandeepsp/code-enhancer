import json
import re
from api.models import (
    EnhanceData, AlreadyOptimalData, CompleteData,
    GenerateData, CodeVariant, TokenUsage, GeneratedLanguageEntry,
)
from api.ai.base import AIResponse


class ParseError(Exception):
    pass


# Field name aliases — AI sometimes uses different names for the same field
_VARIANT_ALIASES = ["variants", "variant", "options", "suggestions", "results"]
_CODE_ALIASES = ["code", "code_snippet", "implementation", "source", "content"]
_TITLE_ALIASES = ["title", "name", "heading", "label"]
_DESCRIPTION_ALIASES = ["description", "desc", "explanation", "summary", "details"]


def _get_field(data: dict, aliases: list[str], default=None):
    """Return the first matching field from a list of aliases."""
    for alias in aliases:
        if alias in data:
            return data[alias]
    return default


def _extract_json_from_text(text: str) -> dict:
    """
    Attempt multiple strategies to extract valid JSON from AI response text.

    Strategy 1: Direct parse after stripping fences
    Strategy 2: Find the largest {...} block in the text
    Strategy 3: Find the first {...} block
    """
    cleaned = text.strip()

    # Strip markdown fences — ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 2: find the outermost {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass

    # Strategy 3: find the first complete {...} block using brace counting
    depth = 0
    json_start = None
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                json_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and json_start is not None:
                try:
                    return json.loads(cleaned[json_start:i + 1])
                except json.JSONDecodeError:
                    json_start = None

    raise ParseError(f"Could not extract valid JSON from AI response. Raw: {text[:300]}")


def _parse_variant(v: dict) -> CodeVariant:
    """Parse a single variant dict with field alias fallbacks."""
    return CodeVariant(
        title=_get_field(v, _TITLE_ALIASES, default="Untitled"),
        description=_get_field(v, _DESCRIPTION_ALIASES, default=""),
        code=_get_field(v, _CODE_ALIASES, default=""),
    )


class ResponseParser:

    def _make_token_usage(self, ai_response: AIResponse) -> TokenUsage:
        return TokenUsage(
            prompt=ai_response.prompt_tokens,
            completion=ai_response.completion_tokens,
            total=ai_response.total_tokens,
        )

    def _parse_variants(self, data: dict) -> list[CodeVariant]:
        raw_variants = _get_field(data, _VARIANT_ALIASES)

        # AI sometimes returns a single variant as a dict instead of a list
        if isinstance(raw_variants, dict):
            raw_variants = [raw_variants]

        if not isinstance(raw_variants, list) or len(raw_variants) == 0:
            # Last resort: if the top-level dict itself looks like a variant, wrap it
            if _get_field(data, _CODE_ALIASES):
                return [_parse_variant(data)]
            raise ParseError("No variants found in AI response")

        return [_parse_variant(v) for v in raw_variants if isinstance(v, dict)]

    def parse_enhance(self, ai_response: AIResponse) -> tuple[bool, EnhanceData | AlreadyOptimalData]:
        data = _extract_json_from_text(ai_response.content)

        if data.get("already_optimal") or data.get("optimal") or data.get("no_changes"):
            return True, AlreadyOptimalData(
                message="Your code already follows best practices.",
                notes=_get_field(data, ["notes", "reasons", "comments"], default=[]),
            )

        return False, EnhanceData(
            variants=self._parse_variants(data),
            token_usage=self._make_token_usage(ai_response),
        )

    def parse_complete(self, ai_response: AIResponse) -> tuple[bool, CompleteData | AlreadyOptimalData]:
        data = _extract_json_from_text(ai_response.content)

        if data.get("already_optimal") or data.get("optimal") or data.get("no_changes"):
            return True, AlreadyOptimalData(
                message="Your code already follows best practices.",
                notes=_get_field(data, ["notes", "reasons", "comments"], default=[]),
            )

        return False, CompleteData(
            variants=self._parse_variants(data),
            token_usage=self._make_token_usage(ai_response),
        )

    def parse_generate(self, ai_response: AIResponse) -> GenerateData:
        data = _extract_json_from_text(ai_response.content)

        if not isinstance(data, dict) or len(data) == 0:
            raise ParseError("Empty or invalid generate response from AI")

        # Known non-language top-level keys to skip
        _skip_keys = {"token_usage", "usage", "error", "already_optimal", "variants"}

        languages = {}
        for lang, entry in data.items():
            if lang in _skip_keys:
                continue
            if not isinstance(entry, dict):
                continue
            languages[lang] = GeneratedLanguageEntry(
                title=_get_field(entry, _TITLE_ALIASES, default="Generated code"),
                description=_get_field(entry, _DESCRIPTION_ALIASES, default=""),
                code=_get_field(entry, _CODE_ALIASES, default=""),
            )

        if not languages:
            raise ParseError("No valid language entries found in generate response")

        return GenerateData(
            languages=languages,
            token_usage=self._make_token_usage(ai_response),
        )
