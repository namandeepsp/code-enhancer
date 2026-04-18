import logging
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from api.models import (
    EnhanceRequest, EnhanceResponse,
    CompleteRequest, CompleteResponse,
    GenerateRequest, GenerateResponse,
    LanguagesResponse, LanguagesData,
)
from api.services import EnhancerService
from api.dependencies import get_enhancer_service
from api.middleware import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["enhancer"])


@router.post("/enhance", response_model=EnhanceResponse, status_code=status.HTTP_200_OK)
async def enhance_code(
    request: EnhanceRequest,
    req: Request,
    service: EnhancerService = Depends(get_enhancer_service),
    _: str = Depends(verify_api_key),
):
    logger.info(f"Enhance request: language={request.language}, size={len(request.code)}")
    return await service.enhance(request)


@router.post("/complete", response_model=CompleteResponse, status_code=status.HTTP_200_OK)
async def complete_code(
    request: CompleteRequest,
    req: Request,
    service: EnhancerService = Depends(get_enhancer_service),
    _: str = Depends(verify_api_key),
):
    logger.info(f"Complete request: language={request.language}, size={len(request.code)}")
    return await service.complete(request)


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_code(
    request: GenerateRequest,
    req: Request,
    service: EnhancerService = Depends(get_enhancer_service),
    _: str = Depends(verify_api_key),
):
    logger.info(f"Generate request: languages={request.languages}, prompt_size={len(request.prompt)}")
    return await service.generate(request)


@router.get("/languages", response_model=LanguagesResponse, status_code=status.HTTP_200_OK)
async def get_languages(
    service: EnhancerService = Depends(get_enhancer_service),
    _: str = Depends(verify_api_key),
):
    languages = service.get_supported_languages()
    return LanguagesResponse(success=True, data=LanguagesData(languages=languages))


@router.get("/health", status_code=status.HTTP_200_OK)
async def enhancer_health(
    service: EnhancerService = Depends(get_enhancer_service),
):
    health = {"service": "enhancer", "status": "healthy", "ai_available": service._ai.is_available()}
    if not service._ai.is_available():
        health["status"] = "degraded"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health)
    return health
