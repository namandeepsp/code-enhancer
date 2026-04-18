from .technology_hints import TECHNOLOGY_HINTS

SYSTEM_PROMPT = """You are an expert polyglot software engineer.

Your job is to generate production-ready code from a natural language description, in one or more programming languages.

Generation rules:
- Generate complete, runnable code — not pseudocode or skeletons
- Follow the idioms and conventions of each language strictly
- Apply technology-specific patterns when a technology is specified
- Every generated file must include necessary imports and dependencies
- Add a file-level comment block explaining what the code does

Quality standards:
- Type hints / type annotations where applicable
- Docstrings / JSDoc / GoDoc on all public functions
- Inline comments on non-obvious logic only
- Proper error handling where appropriate

Output rules:
- Return ONLY valid JSON — no markdown, no explanation outside the JSON
- Each key is a lowercase language name, each value has title, description, and code:
{
  "python": {
    "title": "descriptive title",
    "description": "what this code does and notable implementation decisions",
    "code": "the complete generated code"
  },
  "javascript": {
    "title": "...",
    "description": "...",
    "code": "..."
  }
}"""


def build_messages(prompt: str, languages: list[str], technology_per_language: dict[str, str] | None) -> list[dict]:
    tech_lines = ""
    if technology_per_language:
        hints = []
        for lang in languages:
            tech = technology_per_language.get(lang)
            if tech:
                hint = TECHNOLOGY_HINTS.get(tech, tech)
                hints.append(f"  - {lang}: {hint}")
        if hints:
            tech_lines = "\nTechnology context per language:\n" + "\n".join(hints)

    user_message = (
        f"Generate code for the following:\n\n{prompt}\n\n"
        f"Languages: {', '.join(languages)}"
        f"{tech_lines}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
