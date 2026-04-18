from api.models import EnhanceRequest, CompleteRequest, GenerateRequest
from . import enhance_prompt, complete_prompt, generate_prompt


class PromptRouter:
    def build_enhance(self, request: EnhanceRequest) -> list[dict]:
        return enhance_prompt.build_messages(
            code=request.code,
            language=request.language,
            technology=request.technology,
            context=request.context,
            variants=request.variants,
        )

    def build_complete(self, request: CompleteRequest) -> list[dict]:
        return complete_prompt.build_messages(
            code=request.code,
            language=request.language,
            technology=request.technology,
            context=request.context,
            variants=request.variants,
        )

    def build_generate(self, request: GenerateRequest) -> list[dict]:
        return generate_prompt.build_messages(
            prompt=request.prompt,
            languages=request.languages,
            technology_per_language=request.technology_per_language,
        )
