"""
Settings and configuration endpoints for dark web monitoring
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.services.llm_utils import get_model_choices
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings/llm-providers")
async def get_llm_providers():
    """
    Get available LLM providers and models
    Allows users to see which LLM providers are available and their models
    """
    try:
        available_models = get_model_choices()
        
        # Group models by provider
        providers = {
            "google": [],
            "openai": [],
            "anthropic": [],
            "openrouter": [],
            "local": []
        }
        
        for model in available_models:
            model_lower = model.lower()
            if "gemini" in model_lower:
                providers["google"].append(model)
            elif "gpt" in model_lower and "openrouter" not in model_lower:
                providers["openai"].append(model)
            elif "claude" in model_lower and "openrouter" not in model_lower:
                providers["anthropic"].append(model)
            elif "openrouter" in model_lower:
                providers["openrouter"].append(model)
            else:
                providers["local"].append(model)
        
        # Remove empty providers
        providers = {k: v for k, v in providers.items() if v}
        
        return JSONResponse(
            content={
                "success": True,
                "default_provider": "Google Gemini",
                "default_model": "gemini-2.5-flash",
                "providers": providers,
                "all_models": available_models,
                "description": "Google Gemini is recommended for dark web analysis. Switch providers using model_choice parameter in API calls."
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to retrieve LLM providers: {str(e)}")
        return JSONResponse(
            content={"error": f"Failed to retrieve providers: {str(e)}"},
            status_code=500
        )


@router.get("/settings/pgp-verification")
async def get_pgp_verification_info():
    """
    Get information about PGP verification for .onion sites
    Explains how PGP verification works and what results mean
    """
    return JSONResponse(
        content={
            "success": True,
            "pgp_verification": {
                "enabled": True,
                "description": "Verify .onion site legitimacy using PGP signatures",
                "how_it_works": [
                    "1. Fetches PGP public key from .onion site",
                    "2. Looks for signed files (announcements, proofs, canaries)",
                    "3. Verifies cryptographic signature authenticity",
                    "4. Checks if .onion address is mentioned in signed text",
                    "5. Assigns likelihood score based on verification results"
                ],
                "likelihood_scores": {
                    "Excellent": "Score 4/4 - All verifications passed, site is highly likely legitimate",
                    "Good": "Score 3/4 - Most verifications passed, site is likely legitimate",
                    "Fair": "Score 2/4 - Some verifications passed, site may be legitimate",
                    "Poor": "Score 0-1/4 - No or minimal verifications, site is likely fake/mirrored"
                },
                "verification_factors": {
                    "PGP_key_found": "Site has publicly available PGP key",
                    "PGP_imported": "PGP key successfully imported",
                    "signed_file_found": "Site has PGP-signed files",
                    "signature_valid": "Signature cryptographically verified",
                    "onion_in_text": "Onion address mentioned in signed content"
                }
            }
        },
        status_code=200
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns system status and available services
    """
    return JSONResponse(
        content={
            "success": True,
            "status": "healthy",
            "services": {
                "search": "available",
                "monitoring": "available",
                "alerts": "available",
                "llm_summarizer": "available",
                "pgp_verification": "available"
            }
        },
        status_code=200
    )
