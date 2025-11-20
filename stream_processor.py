
import asyncio
from redis_client import RedisClient
from moderation_graph import ModerationWorkflow
from typing import Dict, Any
import json
from datetime import datetime

class StreamProcessor:
    
    
    def __init__(self, stream_name: str = "content_stream"):
        self.stream_name = stream_name
        self.redis_client = RedisClient()
        self.workflow = ModerationWorkflow()
        self.consumer_group = "moderators"
        self.consumer_name = f"consumer_{datetime.utcnow().timestamp()}"
        
    async def create_consumer_group(self):
        
        try:
            self.redis_client.client.xgroup_create(
                self.stream_name, 
                self.consumer_group, 
                id='0', 
                mkstream=True
            )
        except:
            pass  # Group already exists
    
    async def process_stream(self):
        
        await self.create_consumer_group()
        print(f"Stream processor started for {self.stream_name}")
        
        last_id = '>'
        
        while True:
            try:
                # Read from stream
                messages = self.redis_client.client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: last_id},
                    count=10,
                    block=1000
                )
                
                if messages:
                    for stream_name, stream_messages in messages:
                        for msg_id, msg_data in stream_messages:
                            await self.process_message(msg_id, msg_data)
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\nStopping stream processor...")
                break
            except Exception as e:
                print(f"Stream processing error: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, msg_id: str, msg_data: Dict[str, Any]):
        """Process a single message"""
        try:
            # Decode message
            content_data = json.loads(msg_data.get('data', '{}'))
            
            print(f"Processing stream message: {content_data.get('content_id')}")
            
            # Process through workflow
            result = self.workflow.process_content(content_data)
            
            # Store result
            self.redis_client.store_result(
                content_data['content_id'],
                {
                    "content_id": result.content_id,
                    "severity": result.severity,
                    "action": result.action,
                    "rationale": result.rationale
                }
            )
            
            # Acknowledge message
            self.redis_client.client.xack(
                self.stream_name,
                self.consumer_group,
                msg_id
            )
            
        except Exception as e:
            print(f"Error processing message {msg_id}: {e}")

async def main():
    """Run stream processor"""
    processor = StreamProcessor()
    await processor.process_stream()

if __name__ == "__main__":
    asyncio.run(main())
