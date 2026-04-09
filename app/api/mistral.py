"""
Mistral Vibe API Endpoints
FastAPI router for Mistral Vibe integration
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Dict, Optional
from app.auth import verify_token
from app.services.mistral_client import MistralVibeClient, MistralVibeError
from app.env import get_mistral_config
import logging

router = APIRouter(tags=["Mistral Vibe"])

logger = logging.getLogger("mistral_api")

# Global Mistral Vibe client instance
mistral_client: Optional[MistralVibeClient] = None


def get_mistral_client() -> MistralVibeClient:
    """Get Mistral Vibe client instance"""
    global mistral_client
    if mistral_client is None:
        config = get_mistral_config()
        if not config["enabled"]:
            raise HTTPException(
                status_code=400, 
                detail="Mistral Vibe is not configured. Set MISTRAL_VIBE_API_URL and MISTRAL_VIBE_API_KEY."
            )
        mistral_client = MistralVibeClient(
            api_url=config["api_url"],
            api_key=config["api_key"],
            default_model=config["default_model"],
            timeout=config["timeout"],
            max_retries=config["max_retries"]
        )
    return mistral_client


@router.get("/health", summary="Mistral Vibe Health Check")
async def mistral_health(
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
) -> Dict:
    """
    Check Mistral Vibe API connectivity
    
    Returns:
        - status: Connection status
        - enabled: Whether Mistral Vibe is configured
        - models_available: List of available models (if connected)
    """
    try:
        config = get_mistral_config()
        
        if not config["enabled"]:
            return {
                "status": "disabled",
                "enabled": False,
                "message": "Mistral Vibe is not configured"
            }
        
        client = get_mistral_client()
        
        # Check if client can connect
        is_healthy = await client.health_check()
        
        if is_healthy:
            models = await client.list_models()
            return {
                "status": "healthy",
                "enabled": True,
                "api_url": config["api_url"],
                "default_model": config["default_model"],
                "models_available": [model["id"] for model in models],
                "message": "Mistral Vibe API is available"
            }
        else:
            return {
                "status": "unhealthy",
                "enabled": True,
                "message": "Mistral Vibe API is configured but not responding"
            }
            
    except Exception as e:
        logger.error(f"Mistral Vibe health check failed: {e}")
        return {
            "status": "error",
            "enabled": config.get("enabled", False) if 'config' in locals() else False,
            "message": f"Health check failed: {str(e)}"
        }


@router.post("/chat", summary="Chat Completion")
async def mistral_chat(
    request: Request,
    payload: Dict,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
) -> Dict:
    """
    Get chat completion from Mistral Vibe
    
    Request body should contain:
    - messages: List of message objects with 'role' and 'content'
    - model: (optional) Model to use
    - temperature: (optional) Temperature for response
    - max_tokens: (optional) Maximum tokens to generate
    
    Example:
    {
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "model": "mistral-small",
        "temperature": 0.7
    }
    """
    try:
        client = get_mistral_client()
        
        messages = payload.get("messages", [])
        model = payload.get("model")
        temperature = payload.get("temperature", 0.7)
        max_tokens = payload.get("max_tokens")
        
        if not messages:
            raise HTTPException(status_code=400, detail="Messages are required")
        
        result = await client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            "success": True,
            "result": result,
            "model_used": model or client.default_model
        }
        
    except MistralVibeError as e:
        raise HTTPException(status_code=502, detail=f"Mistral Vibe error: {str(e)}")
    except Exception as e:
        logger.error(f"Mistral Vibe chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/models", summary="List Available Models")
async def mistral_models(
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
) -> Dict:
    """
    List available Mistral Vibe models
    
    Returns:
        - models: List of available models with details
        - default_model: Currently configured default model
    """
    try:
        config = get_mistral_config()
        
        if not config["enabled"]:
            raise HTTPException(
                status_code=400,
                detail="Mistral Vibe is not configured"
            )
        
        client = get_mistral_client()
        models = await client.list_models()
        
        return {
            "models": models,
            "default_model": config["default_model"],
            "count": len(models)
        }
        
    except MistralVibeError as e:
        raise HTTPException(status_code=502, detail=f"Mistral Vibe error: {str(e)}")
    except Exception as e:
        logger.error(f"Mistral Vibe models error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/embeddings", summary="Create Embeddings")
async def mistral_embeddings(
    payload: Dict,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
) -> Dict:
    """
    Create embeddings using Mistral Vibe
    
    Request body should contain:
    - input: Text to embed
    - model: (optional) Model to use
    
    Example:
    {
        "input": "Sample text to embed",
        "model": "mistral-embed"
    }
    """
    try:
        client = get_mistral_client()
        
        input_text = payload.get("input")
        model = payload.get("model")
        
        if not input_text:
            raise HTTPException(status_code=400, detail="Input text is required")
        
        result = await client.create_embedding(input_text, model)
        
        return {
            "success": True,
            "result": result,
            "model_used": model or client.default_model
        }
        
    except MistralVibeError as e:
        raise HTTPException(status_code=502, detail=f"Mistral Vibe error: {str(e)}")
    except Exception as e:
        logger.error(f"Mistral Vibe embeddings error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")