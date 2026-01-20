"""Pydantic models for API"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class FileContent(BaseModel):
    """File content model"""
    path: str = Field(..., description="Relative path from /config")
    content: str = Field(..., description="File content")
    create_backup: bool = Field(True, description="Create backup before writing")
    commit_message: Optional[str] = Field(None, description="Custom commit message for Git backup (e.g., 'Fix automation: add motion sensor trigger')")

class FileAppend(BaseModel):
    """File append model"""
    path: str
    content: str
    commit_message: Optional[str] = Field(None, description="Custom commit message for Git backup (e.g., 'Add new automation to automations.yaml')")

class HelperCreate(BaseModel):
    """Helper creation model"""
    type: str = Field(
        ...,
        description=(
            "Helper type: input_boolean, input_text, input_number, input_datetime, "
            "input_select, group, utility_meter"
        ),
    )
    config: Dict[str, Any] = Field(..., description="Helper configuration including 'name' and other options")
    commit_message: Optional[str] = Field(None, description="Custom commit message for Git backup (e.g., 'Add helper: climate system enabled switch')")

class AutomationData(BaseModel):
    """Automation data model"""
    id: Optional[str] = None
    alias: str
    description: Optional[str] = None
    trigger: List[Dict[str, Any]]
    condition: Optional[List[Dict[str, Any]]] = []
    action: List[Dict[str, Any]]
    mode: str = "single"
    commit_message: Optional[str] = Field(None, description="Custom commit message for Git backup (e.g., 'Add automation: motion sensor light control')")

class ScriptData(BaseModel):
    """Script data model"""
    entity_id: str = Field(..., description="Script entity ID without 'script.' prefix")
    alias: str
    sequence: List[Dict[str, Any]]
    mode: str = "single"
    icon: Optional[str] = None
    description: Optional[str] = None
    commit_message: Optional[str] = Field(None, description="Custom commit message for Git backup (e.g., 'Add script: climate control startup')")

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

class EntityRemoveRequest(BaseModel):
    """Entity removal request model"""
    entity_id: str = Field(..., description="Entity ID to remove from registry")

class AreaRemoveRequest(BaseModel):
    """Area removal request model"""
    area_id: str = Field(..., description="Area ID to remove from registry")

class DeviceRemoveRequest(BaseModel):
    """Device removal request model"""
    device_id: str = Field(..., description="Device ID to remove from registry")

class Response(BaseModel):
    """Generic response model"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None

