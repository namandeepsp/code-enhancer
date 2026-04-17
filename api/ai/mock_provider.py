import json
from .base import AIProvider, AIResponse
from .deepseek_provider import AIProviderError


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


class MockAIProviderUnreliable(AIProvider):
    """
    Returns malformed or edge-case responses to test parser resilience.
    Cycles through different failure modes on each call.
    """

    def __init__(self):
        self._call_count = 0

    def is_available(self) -> bool:
        return True

    async def complete(self, messages: list[dict], timeout: int) -> AIResponse:
        self._call_count += 1
        mode = self._call_count % 8

        if mode == 1:
            # JSON wrapped in markdown fences
            content = '```json\n{"already_optimal": false, "variants": [{"title": "T", "description": "D", "code": "x = 1"}]}\n```'
        elif mode == 2:
            # Field name aliases — variant instead of variants
            content = json.dumps({"already_optimal": False, "variant": [{"title": "T", "description": "D", "code": "x = 1"}]})
        elif mode == 3:
            # already_optimal with alias field name
            content = json.dumps({"optimal": True, "reasons": ["code is clean"]})
        elif mode == 4:
            # Extra commentary before JSON
            content = 'Here is the enhanced code:\n{"already_optimal": false, "variants": [{"title": "T", "description": "D", "code": "x = 1"}]}'
        elif mode == 5:
            # Single variant as dict instead of list
            content = json.dumps({"already_optimal": False, "variants": {"title": "T", "description": "D", "code": "x = 1"}})
        elif mode == 6:
            # code field alias
            content = json.dumps({"already_optimal": False, "variants": [{"title": "T", "description": "D", "implementation": "x = 1"}]})
        elif mode == 7:
            # Simulate retryable AI provider error
            raise AIProviderError("Service temporarily unavailable", status_code=503, retryable=True)
        else:
            # Normal valid response
            content = json.dumps({"already_optimal": False, "variants": [{"title": "T", "description": "D", "code": "x = 1"}]})

        return AIResponse(content=content, prompt_tokens=10, completion_tokens=20, total_tokens=30)
