"""
AI Instructions API
Provides detailed instructions for AI assistants (like Cursor AI)
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from app.ai_instructions import load_all_instructions

router = APIRouter(tags=["AI Instructions"])


@router.get(
    "/instructions",
    response_class=PlainTextResponse,
    summary="Get AI Assistant Instructions",
    description="Returns detailed instructions for AI assistants on how to safely use this API"
)
async def get_ai_instructions():
    """
    Get complete instructions for AI assistants (like Cursor AI).
    
    Instructions are loaded from markdown files in app/ai_instructions/docs/
    
    This endpoint provides:
    - Safety protocols
    - Step-by-step workflow
    - Best practices
    - Error handling guidelines
    - Dashboard generation guides
    
    Returns plain text for easy consumption by AI.
    """
    from app.main import AGENT_VERSION
    return load_all_instructions(version=AGENT_VERSION)
