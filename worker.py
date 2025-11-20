import time
from redis_client import RedisClient
from moderation_graph import ModerationWorkflow
from models import ModerationDecision
from config import ANTHROPIC_API_KEY
import anthropic

def create_llm_client():
    """Create Anthropic client if API key is available"""
    if ANTHROPIC_API_KEY:
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return None

def process_content_job(workflow: ModerationWorkflow, redis_client: RedisClient, content_data: dict):
    """Process a single content moderation job"""
    try:
        print(f"Processing content: {content_data['content_id']}")
        
        # Process through workflow
        result_state = workflow.process_content(content_data)
        
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
            status="completed" if not result_state.requires_human_review else "review"
        )
        
        # Store results
        redis_client.store_result(
            content_data["content_id"],
            decision.model_dump(mode='json')
        )
        redis_client.store_decision(decision.model_dump(mode='json'))
        
        print(f"Completed: {content_data['content_id']} - Action: {decision.action}")
        
    except Exception as e:
        print(f"Error processing content {content_data.get('content_id')}: {e}")

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
