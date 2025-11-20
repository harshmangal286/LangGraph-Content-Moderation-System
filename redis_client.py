import redis
import json
from typing import Optional, Dict, Any
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, CONTENT_QUEUE, RESULT_QUEUE

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
    
    def enqueue_content(self, content_data: Dict[str, Any]) -> str:
        """Add content to moderation queue"""
        content_id = content_data["content_id"]
        self.client.lpush(CONTENT_QUEUE, json.dumps(content_data))
        return content_id
    
    def dequeue_content(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Get next content from queue"""
        result = self.client.brpop(CONTENT_QUEUE, timeout=timeout)
        if result:
            _, data = result
            return json.loads(data)
        return None
    
    def store_result(self, content_id: str, result: Dict[str, Any]):
        """Store moderation result"""
        key = f"result:{content_id}"
        self.client.setex(key, 3600, json.dumps(result))  # 1 hour TTL
        self.client.lpush(RESULT_QUEUE, json.dumps(result))
    
    def get_result(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve moderation result"""
        key = f"result:{content_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def track_user_posts(self, user_id: str, time_window: int = 60) -> int:
        """Track user post frequency for spam detection"""
        key = f"user_posts:{user_id}"
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, time_window)
        result = pipe.execute()
        return result[0]
    
    def get_user_post_count(self, user_id: str) -> int:
        """Get current user post count"""
        key = f"user_posts:{user_id}"
        count = self.client.get(key)
        return int(count) if count else 0
    
    def store_decision(self, decision: Dict[str, Any]):
        """Store decision in database"""
        content_id = decision["content_id"]
        key = f"decision:{content_id}"
        self.client.setex(key, 86400, json.dumps(decision))  # 24 hour TTL
    
    def get_decision(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored decision"""
        key = f"decision:{content_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except:
            return False
