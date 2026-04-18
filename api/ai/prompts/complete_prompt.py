from .technology_hints import TECHNOLOGY_HINTS

SYSTEM_PROMPT = """You are an expert software engineer specializing in completing partial or stub code.

Your job is to implement incomplete code (empty functions, pass bodies, TODO comments) with the best possible implementation.

Completion rules:
- Infer intent from the function name, parameters, docstring, and any comments
- Use the provided file context to match existing patterns, data models, and conventions exactly
- Do not change function signatures unless they are clearly wrong
- Complete ALL stubs in the submitted code, not just the first one
- Return the complete function or file — not just the filled-in parts

Quality standards:
- Type hints / type annotations where applicable
- Docstrings / JSDoc / GoDoc on all public functions
- Inline comments on non-obvious logic only
- Proper error handling where appropriate
- No magic numbers — use named constants

Output rules:
- Return ONLY valid JSON — no markdown, no explanation outside the JSON
- Format:
{
  "already_optimal": false,
  "variants": [
    {
      "title": "short descriptive title",
      "description": "implementation approach and key decisions",
      "code": "the complete implemented code"
    }
  ]
}"""


def build_messages(code: str, language: str, technology: str | None, context: str | None, variants: int) -> list[dict]:
    tech_hint = f"\nTechnology: {TECHNOLOGY_HINTS.get(technology, technology)}" if technology else ""
    context_section = f"\nFull file context:\n{context}" if context else ""

    user_message = (
        f"Language: {language}{tech_hint}\n\n"
        f"Incomplete code to implement:\n{code}"
        f"{context_section}\n\n"
        f"Return {variants} variant(s)."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
