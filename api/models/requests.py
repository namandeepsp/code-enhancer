from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class EnhanceRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to enhance")
    language: str = Field(..., min_length=1, description="Programming language")
    technology: Optional[str] = Field(None, description="Framework or technology (e.g. fastapi, react, gin)")
    context: Optional[str] = Field(None, description="Full file content for additional context")
    variants: int = Field(1, ge=1, le=3, description="Number of variants to return (1-3)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "def add(a, b):\n    return a",
                "language": "python",
                "technology": "fastapi",
                "context": None,
                "variants": 2,
            }
        }
    )


class CompleteRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Partial or stub code to complete")
    language: str = Field(..., min_length=1, description="Programming language")
    technology: Optional[str] = Field(None, description="Framework or technology")
    context: Optional[str] = Field(None, description="Full file content so AI understands surrounding code")
    variants: int = Field(1, ge=1, le=3, description="Number of variants to return (1-3)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "def calculate_discount(price, user_tier):\n    pass",
                "language": "python",
                "technology": "django",
                "context": "# models.py content here",
                "variants": 1,
            }
        }
    )


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language description of what to generate")
    languages: list[str] = Field(..., min_length=1, description="Languages to generate code in")
    technology_per_language: Optional[dict[str, str]] = Field(
        None, description="Technology per language e.g. {python: fastapi, javascript: express}"
    )
    variants: int = Field(1, ge=1, le=3, description="Number of variants per language (1-3)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "Create a JWT authentication middleware",
                "languages": ["python", "javascript"],
                "technology_per_language": {"python": "fastapi", "javascript": "express"},
                "variants": 1,
            }
        }
    )
