"""
Mistral Vibe Client
Async HTTP client for Mistral Vibe API
"""
import os
import logging
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from app.utils.logger import setup_logger

logger = setup_logger("mistral_client", os.getenv("LOG_LEVEL", "info").upper())


class MistralVibeClient:
    """Async client for Mistral Vibe API"""
    
    def __init__(self, api_url: str, api_key: str, default_model: str = "mistral-tiny", 
                 timeout: int = 30, max_retries: int = 3):
        """Initialize Mistral Vibe client"""
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the client session"""
        if self.session is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout
            )
            logger.info(f"✅ Mistral Vibe client started - URL: {self.api_url}")
        
    async def stop(self):
        """Stop the client session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("✅ Mistral Vibe client stopped")
    
    async def _request(self, method: str, endpoint: str, 
                      payload: Optional[Dict] = None, 
                      retries: int = 0) -> Dict:
        """Make API request with retry logic"""
        if not self.session:
            await self.start()
        
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                response = await self.session.get(url, params=payload)
            else:
                response = await self.session.request(
                    method, url, json=payload
                )
            
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"Mistral Vibe API error {response.status}: {error_text}")
                raise MistralVibeError(f"API error {response.status}: {error_text}")
                
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            if retries < self.max_retries:
                logger.warning(f"Mistral Vibe request failed (attempt {retries + 1}/{self.max_retries}): {e}")
                await asyncio.sleep(1 * (retries + 1))  # Exponential backoff
                return await self._request(method, endpoint, payload, retries + 1)
            else:
                logger.error(f"Mistral Vibe request failed after {self.max_retries} retries: {e}")
                raise MistralVibeError(f"Request failed after {self.max_retries} retries: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if Mistral Vibe API is available"""
        try:
            # Try a simple health check or model list endpoint
            result = await self._request("GET", "v1/models")
            return True
        except Exception as e:
            logger.warning(f"Mistral Vibe health check failed: {e}")
            return False
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                             model: Optional[str] = None, 
                             temperature: float = 0.7, 
                             max_tokens: Optional[int] = None) -> Dict:
        """Get chat completion from Mistral Vibe"""
        model = model or self.default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        logger.debug(f"Sending chat completion request to Mistral Vibe: {model}")
        
        try:
            result = await self._request("POST", "v1/chat/completions", payload)
            logger.debug(f"Received chat completion response from Mistral Vibe")
            return result
        except Exception as e:
            logger.error(f"Mistral Vibe chat completion failed: {e}")
            raise
    
    async def list_models(self) -> List[Dict]:
        """List available models"""
        try:
            result = await self._request("GET", "v1/models")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Mistral Vibe list models failed: {e}")
            raise
    
    async def create_embedding(self, input_text: str, 
                              model: Optional[str] = None) -> Dict:
        """Create embeddings for text"""
        model = model or self.default_model
        
        payload = {
            "model": model,
            "input": input_text
        }
        
        try:
            result = await self._request("POST", "v1/embeddings", payload)
            return result
        except Exception as e:
            logger.error(f"Mistral Vibe embedding failed: {e}")
            raise


class MistralVibeError(Exception):
    """Mistral Vibe specific exception"""
    pass