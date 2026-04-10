"""Pydantic models for API"""
import json
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List


def _parse_json_string(value: Any) -> Any:
    """Parse JSON object/array encoded as string."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in ("{", "["):
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value

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

    @model_validator(mode='before')
    @classmethod
    def parse_config_if_json_string(cls, data):
        if isinstance(data, dict) and 'config' in data:
            data['config'] = _parse_json_string(data['config'])
        return data

class AutomationData(BaseModel):
    """Automation data model.

    Accepts both HA legacy (trigger/condition/action) and modern
    (triggers/conditions/actions) field names. Plural forms are
    normalized to singular during validation.
    """
    id: Optional[str] = None
    alias: str
    description: Optional[str] = None
    trigger: Optional[List[Dict[str, Any]]] = None
    condition: Optional[List[Dict[str, Any]]] = []
    action: Optional[List[Dict[str, Any]]] = None
    triggers: Optional[List[Dict[str, Any]]] = Field(None, exclude=True)
    conditions: Optional[List[Dict[str, Any]]] = Field(None, exclude=True)
    actions: Optional[List[Dict[str, Any]]] = Field(None, exclude=True)
    mode: str = "single"
    commit_message: Optional[str] = Field(None, description="Custom commit message for Git backup (e.g., 'Add automation: motion sensor light control')")

    @model_validator(mode='before')
    @classmethod
    def normalize_plural_fields(cls, data):
        """Accept triggers/conditions/actions (plural) and map to singular."""
        if isinstance(data, dict):
            for key in ('trigger', 'condition', 'action', 'triggers', 'conditions', 'actions'):
                if key in data:
                    data[key] = _parse_json_string(data[key])
            if 'triggers' in data and 'trigger' not in data:
                data['trigger'] = data['triggers']
            if 'conditions' in data and 'condition' not in data:
                data['condition'] = data['conditions']
            if 'actions' in data and 'action' not in data:
                data['action'] = data['actions']
        return data

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

