from pydantic import BaseModel
from typing import Optional, Any


# --- Shared base ---

class ApiResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    cached: bool = False


# --- Variant (used by enhance + complete) ---

class CodeVariant(BaseModel):
    title: str
    description: str
    code: str


# --- Token usage (attached to every AI response) ---

class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int


# --- Enhance ---

class EnhanceData(BaseModel):
    variants: list[CodeVariant]
    token_usage: TokenUsage


class AlreadyOptimalData(BaseModel):
    message: str
    notes: list[str]


class EnhanceResponse(ApiResponse):
    task: str = "enhance"
    already_optimal: bool = False
    data: Optional[EnhanceData | AlreadyOptimalData] = None


# --- Complete ---

class CompleteData(BaseModel):
    variants: list[CodeVariant]
    token_usage: TokenUsage


class CompleteResponse(ApiResponse):
    task: str = "complete"
    already_optimal: bool = False
    data: Optional[CompleteData | AlreadyOptimalData] = None


# --- Generate ---

class GeneratedLanguageEntry(BaseModel):
    title: str
    description: str
    code: str


class GenerateData(BaseModel):
    languages: dict[str, GeneratedLanguageEntry]
    token_usage: TokenUsage


class GenerateResponse(ApiResponse):
    task: str = "generate"
    already_optimal: bool = False
    data: Optional[GenerateData] = None


# --- Languages ---

class LanguagesData(BaseModel):
    languages: list[str]


class LanguagesResponse(ApiResponse):
    data: Optional[LanguagesData] = None
