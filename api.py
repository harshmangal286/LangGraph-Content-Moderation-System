from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from models import (
    ContentSubmission, ModerationDecision, AppealRequest, 
    AppealDecision, ModerationAction, WorkflowState
)
from redis_client import RedisClient
from moderation_graph import ModerationWorkflow
from config import SPAM_TIME_WINDOW, ANTHROPIC_API_KEY
import uuid
from datetime import datetime
from typing import Dict, Any
import anthropic

app = FastAPI(
    title="Content Moderation API",
    description="AI-powered content moderation system using LangGraph",
    version="1.0.0"
)

redis_client = RedisClient()

def get_llm_client():
    if ANTHROPIC_API_KEY:
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return None

@app.get("/")
async def root():
    return {
        "service": "Content Moderation API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    redis_ok = redis_client.ping()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/moderate", response_model=Dict[str, Any])
async def submit_content(submission: ContentSubmission):
    """Submit content for moderation"""
    
    # Generate content ID
    content_id = str(uuid.uuid4())
    
    # Track user posts for spam detection
    post_count = redis_client.track_user_posts(
        submission.user_id, 
        SPAM_TIME_WINDOW
    )
    
    # Prepare content data
    content_data = {
        "content_id": content_id,
        "user_id": submission.user_id,
        "content": submission.content,
        "content_type": submission.content_type,
        "metadata": {
            **submission.metadata,
            "recent_post_count": post_count,
            "submitted_at": datetime.utcnow().isoformat()
        }
    }
    
    # Enqueue for processing
    redis_client.enqueue_content(content_data)
    
    return {
        "content_id": content_id,
        "status": "queued",
        "message": "Content submitted for moderation",
        "estimated_time": "Processing typically completes within 5-10 seconds"
    }

@app.get("/status/{content_id}", response_model=Dict[str, Any])
async def get_moderation_status(content_id: str):
    """Get moderation status and decision"""
    
    result = redis_client.get_result(content_id)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail="Content not found or still processing"
        )
    
    return result

@app.post("/appeal", response_model=Dict[str, Any])
async def submit_appeal(appeal: AppealRequest):
    """Submit an appeal for a moderation decision"""
    
    # Get original decision
    original = redis_client.get_decision(appeal.content_id)
    
    if not original:
        raise HTTPException(
            status_code=404,
            detail="Original decision not found"
        )
    
    # Verify user
    if original["user_id"] != appeal.user_id:
        raise HTTPException(
            status_code=403,
            detail="User ID does not match original submission"
        )
    
    # Process appeal through workflow
    llm_client = get_llm_client()
    workflow = ModerationWorkflow(llm_client)
    
    appeal_state = {
        "content_id": appeal.content_id,
        "user_id": appeal.user_id,
        "content": original["content"],
        "content_type": "text",
        "metadata": {
            "is_appeal": True,
            "appeal_reason": appeal.appeal_reason,
            "additional_context": appeal.additional_context,
            "original_severity": original["severity"],
            "original_action": original["action"]
        }
    }
    
    result_state = workflow.process_appeal(appeal_state)
    
    # Determine if appeal is granted
    appeal_granted = result_state.severity < original["severity"] * 0.8
    new_action = result_state.action if appeal_granted else original["action"]
    
    appeal_decision = AppealDecision(
        content_id=appeal.content_id,
        original_decision=ModerationDecision(**original),
        appeal_granted=appeal_granted,
        new_action=new_action,
        moderator_notes=f"Appeal review: {result_state.rationale}",
        reviewed_by="system"
    )
    
    # Store appeal decision
    redis_client.store_decision(appeal_decision.model_dump(mode='json'))
    
    return appeal_decision.model_dump(mode='json')

@app.post("/moderator/review/{content_id}")
async def moderator_review(
    content_id: str,
    action: ModerationAction,
    notes: str,
    moderator_id: str
):
    """Moderator manually reviews and modifies a decision"""
    
    original = redis_client.get_decision(content_id)
    
    if not original:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    # Create updated decision
    updated_decision = ModerationDecision(**original)
    updated_decision.action = action
    updated_decision.moderator_notes = notes
    updated_decision.status = "completed"
    updated_decision.timestamp = datetime.utcnow()
    
    # Store updated decision
    redis_client.store_decision(updated_decision.model_dump(mode='json'))
    redis_client.store_result(content_id, updated_decision.model_dump(mode='json'))
    
    return {
        "content_id": content_id,
        "action": action,
        "moderator": moderator_id,
        "notes": notes,
        "timestamp": updated_decision.timestamp.isoformat()
    }

@app.get("/stats/user/{user_id}")
async def get_user_stats(user_id: str):
    """Get user moderation statistics"""
    post_count = redis_client.get_user_post_count(user_id)
    
    return {
        "user_id": user_id,
        "recent_post_count": post_count,
        "time_window_seconds": SPAM_TIME_WINDOW
    }

if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT
    uvicorn.run(app, host=API_HOST, port=API_PORT)
