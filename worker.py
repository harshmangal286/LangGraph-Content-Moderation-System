import time
from redis_client import RedisClient
from moderation_graph import ModerationWorkflow
from models import ModerationDecision
from config import ANTHROPIC_API_KEY
import anthropic
from datetime import datetime

def create_llm_client():
    """Create Anthropic client if API key is available"""
    if ANTHROPIC_API_KEY:
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return None

def process_content_job(workflow: ModerationWorkflow, redis_client: RedisClient, content_data: dict):
    """Process a single content moderation job"""
    content_id = content_data.get('content_id', 'unknown')
    
    try:
        print(f"Processing content: {content_id}")
        
        # Process through workflow
        result_state = workflow.process_content(content_data)
        
        # Determine status based on whether human review is required
        if result_state.requires_human_review:
            status = "pending"  # Changed from "review" to valid enum value
        else:
            status = "completed"
        
        # Create decision object
        decision = ModerationDecision(
            content_id=result_state.content_id,
            user_id=result_state.user_id,
            content=result_state.content,
            severity=result_state.severity,
            action=result_state.action,
            rationale=result_state.rationale,
            detected_issues=result_state.detected_issues,
            language=result_state.language,
            status=status
        )
        
        # Store results
        redis_client.store_result(
            content_data["content_id"],
            decision.model_dump(mode='json')
        )
        redis_client.store_decision(decision.model_dump(mode='json'))
        
        print(f"✅ Completed: {content_id} - Action: {decision.action}, Severity: {decision.severity:.2f}")
        
    except Exception as e:
        print(f"❌ Error processing content {content_id}: {e}")
        
        # Store error result so status endpoint doesn't hang
        try:
            error_result = {
                "content_id": content_id,
                "severity": 0.0,
                "action": "review",
                "rationale": f"Error during processing: {str(e)}",
                "detected_issues": ["processing_error"],
                "status": "pending",  # Valid enum value
                "user_id": content_data.get("user_id", "unknown"),
                "content": content_data.get("content", ""),
                "language": "en",
                "timestamp": datetime.utcnow().isoformat()
            }
            redis_client.store_result(content_id, error_result)
        except Exception as store_error:
            print(f"❌ Failed to store error result: {store_error}")

def main():
    """Main worker loop"""
    print("Starting moderation worker...")
    
    redis_client = RedisClient()
    if not redis_client.ping():
        print("ERROR: Cannot connect to Redis. Please start Redis server.")
        return
    
    llm_client = create_llm_client()
    if llm_client:
        print("Using Claude Sonnet 4.5 for content analysis")
    else:
        print("Using rule-based analysis (set ANTHROPIC_API_KEY for LLM analysis)")
    
    workflow = ModerationWorkflow(llm_client)
    print("Worker ready. Waiting for content...")
    
    while True:
        try:
            # Get next content from queue
            content_data = redis_client.dequeue_content(timeout=5)
            
            if content_data:
                process_content_job(workflow, redis_client, content_data)
            else:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down worker...")
            break
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
