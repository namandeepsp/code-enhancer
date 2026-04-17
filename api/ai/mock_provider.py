import json
from .base import AIProvider, AIResponse


class MockAIProvider(AIProvider):
    """
    Deterministic AI provider for testing.
    Returns hardcoded valid responses for each task type detected from the messages.
    No real API calls — safe to use in CI.
    """

    def is_available(self) -> bool:
        return True

    async def complete(self, messages: list[dict], timeout: int) -> AIResponse:
        user_message = next((m["content"] for m in messages if m["role"] == "user"), "")

        if "enhance" in user_message.lower() or "improve" in user_message.lower():
            content = self._enhance_response()
        elif "complete" in user_message.lower() or "implement" in user_message.lower():
            content = self._complete_response()
        elif "generate" in user_message.lower():
            content = self._generate_response(user_message)
        else:
            content = self._enhance_response()

        return AIResponse(content=content, prompt_tokens=50, completion_tokens=100, total_tokens=150)

    def _enhance_response(self) -> str:
        return json.dumps({
            "already_optimal": False,
            "variants": [
                {
                    "title": "Enhanced version",
                    "description": "Added type hints and docstring",
                    "code": "def add(a: float, b: float) -> float:\n    \"\"\"Return the sum of a and b.\"\"\"\n    return a + b"
                }
            ]
        })

    def _complete_response(self) -> str:
        return json.dumps({
            "already_optimal": False,
            "variants": [
                {
                    "title": "Completed implementation",
                    "description": "Implemented the stub with proper logic",
                    "code": "def calculate(x: int, y: int) -> int:\n    \"\"\"Calculate and return the result.\"\"\"\n    return x + y"
                }
            ]
        })

    def _generate_response(self, user_message: str) -> str:
        result = {}
        for lang in ["python", "javascript", "go", "java"]:
            if lang in user_message.lower():
                result[lang] = {
                    "title": f"Generated {lang.capitalize()} code",
                    "description": f"Implementation in {lang}",
                    "code": f"# Generated {lang} code\ndef example():\n    pass"
                }
        if not result:
            result["python"] = {
                "title": "Generated Python code",
                "description": "Default Python implementation",
                "code": "# Generated code\ndef example():\n    pass"
            }
        return json.dumps(result)
