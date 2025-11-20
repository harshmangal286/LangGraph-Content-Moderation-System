from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"

class ModerationAction(str, Enum):
    APPROVE = "approve"
    FLAG = "flag"
    REVIEW = "review"
    SUSPEND = "suspend"

class ModerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    APPEALED = "appealed"

class ContentSubmission(BaseModel):
    content: str
    content_type: ContentType = ContentType.TEXT
    user_id: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ModerationDecision(BaseModel):
    content_id: str
    user_id: str
    content: str
    severity: float
    action: ModerationAction
    rationale: str
    detected_issues: List[str]
    language: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: ModerationStatus = ModerationStatus.COMPLETED
    moderator_notes: Optional[str] = None

class AppealRequest(BaseModel):
    content_id: str
    user_id: str
    appeal_reason: str
    additional_context: Optional[str] = None

class AppealDecision(BaseModel):
    content_id: str
    original_decision: ModerationDecision
    appeal_granted: bool
    new_action: ModerationAction
    moderator_notes: str
    reviewed_by: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WorkflowState(BaseModel):
    content_id: str
    user_id: str
    content: str
    content_type: ContentType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Analysis results
    language: Optional[str] = None
    toxicity_score: float = 0.0
    spam_score: float = 0.0
    sarcasm_score: float = 0.0
    detected_issues: List[str] = Field(default_factory=list)
    
    # Decision
    severity: float = 0.0
    action: Optional[ModerationAction] = None
    rationale: str = ""
    requires_human_review: bool = False
    
    # Appeal data
    is_appeal: bool = False
    appeal_reason: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
