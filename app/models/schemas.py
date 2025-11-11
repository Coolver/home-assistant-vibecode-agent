"""Pydantic models for API"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class FileContent(BaseModel):
    """File content model"""
    path: str = Field(..., description="Relative path from /config")
    content: str = Field(..., description="File content")
    create_backup: bool = Field(True, description="Create backup before writing")

class FileAppend(BaseModel):
    """File append model"""
    path: str
    content: str

class HelperCreate(BaseModel):
    """Helper creation model"""
    type: str = Field(..., description="Helper type: input_boolean, input_text, input_number, input_datetime, input_select")
    config: Dict[str, Any] = Field(..., description="Helper configuration including 'name' and other options")

class AutomationData(BaseModel):
    """Automation data model"""
    id: Optional[str] = None
    alias: str
    description: Optional[str] = None
    trigger: List[Dict[str, Any]]
    condition: Optional[List[Dict[str, Any]]] = []
    action: List[Dict[str, Any]]
    mode: str = "single"

class ScriptData(BaseModel):
    """Script data model"""
    entity_id: str = Field(..., description="Script entity ID without 'script.' prefix")
    alias: str
    sequence: List[Dict[str, Any]]
    mode: str = "single"
    icon: Optional[str] = None
    description: Optional[str] = None

class ServiceCall(BaseModel):
    """Service call model"""
    domain: str
    service: str
    data: Optional[Dict[str, Any]] = {}
    target: Optional[Dict[str, Any]] = None

class BackupRequest(BaseModel):
    """Backup request model"""
    message: Optional[str] = None

class RollbackRequest(BaseModel):
    """Rollback request model"""
    commit_hash: str

class Response(BaseModel):
    """Generic response model"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None

