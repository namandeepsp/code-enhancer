from .technology_hints import TECHNOLOGY_HINTS

SYSTEM_PROMPT = """You are an expert code reviewer and enhancer.

Your job is to analyze submitted code and return an improved version following industry best practices.

Quality checklist — apply to every enhancement:
- Correct and complete logic
- Proper naming (variables, functions, classes)
- Type hints / type annotations where applicable
- Docstrings / JSDoc / GoDoc on all public functions
- Inline comments on non-obvious logic only (never comment the obvious)
- No dead code, no unused imports
- Error handling where appropriate
- No magic numbers — use named constants

ALREADY_OPTIMAL rule:
If the submitted code already passes ALL checklist items, respond with:
{"already_optimal": true, "notes": ["reason 1", "reason 2"]}
Do NOT fabricate enhancements just to have something to return.

Output rules:
- Return ONLY valid JSON — no markdown, no explanation outside the JSON
- When enhancements exist, return:
{
  "already_optimal": false,
  "variants": [
    {
      "title": "short descriptive title",
      "description": "what changed and why",
      "code": "the complete enhanced code"
    }
  ]
}"""


def build_messages(code: str, language: str, technology: str | None, context: str | None, variants: int) -> list[dict]:
    tech_hint = f"\nTechnology: {TECHNOLOGY_HINTS.get(technology, technology)}" if technology else ""
    context_section = f"\nFull file context:\n{context}" if context else ""

    user_message = (
        f"Language: {language}{tech_hint}\n\n"
        f"Code to enhance:\n{code}"
        f"{context_section}\n\n"
        f"Return {variants} variant(s)."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
