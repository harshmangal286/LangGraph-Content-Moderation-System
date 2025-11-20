# AI-Powered Content Moderation System

A production-ready content moderation system built with **LangGraph**, **Claude Sonnet 4.5**, **Redis**, and **FastAPI**. The system automatically analyzes content for toxicity, spam, and policy violations using a graph-based workflow.

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   FastAPI   │────▶│ Redis Queue  │────▶│   Worker   │
│     API     │     │              │     │ (LangGraph)│
└─────────────┘     └──────────────┘     └────────────┘
       │                                         │
       │                                         ▼
       │                                  ┌──────────────┐
       └──────────────────────────────────│Claude Sonnet │
                  Results                 │     4.5      │
                                         └──────────────┘
```

### Components

1. **LangGraph Workflow**: Multi-node graph for content analysis
   - Language detection
   - Content analysis (toxicity, spam, sarcasm)
   - Spam burst detection
   - Severity calculation
   - Decision making with human review routing

2. **Redis**: Message queue and data storage
   - Content queue for async processing
   - Result storage with TTL
   - User activity tracking for spam detection

3. **FastAPI**: REST API for content submission and management
   - Submit content for moderation
   - Check moderation status
   - Appeal decisions
   - Moderator review endpoints

4. **Worker**: Background processor consuming from Redis queue

## 📋 Prerequisites

- Python 3.8+
- Redis server
- Anthropic API key (optional, falls back to rule-based analysis)

## 🚀 Installation

### 1. Clone and Setup

```bash
cd c:\Users\Dell\OneDrive\Desktop\python\assignmentintership
pip install -r requirements.txt
```

### 2. Install Redis

**Windows:**
```bash
# Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases
# Or use WSL/Docker
docker run -d -p 6379:6379 redis:latest
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Mac
brew install redis
brew services start redis
```

### 3. Configure Environment (Optional)

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=your_api_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
API_HOST=0.0.0.0
API_PORT=8000
```

If you don't have an Anthropic API key, the system will use rule-based analysis.

## 🎮 Running the System

### Start Components (3 Terminal Windows)

**Terminal 1 - Redis** (if not running as service):
```bash
redis-server
```

**Terminal 2 - Worker**:
```bash
python worker.py
```

**Terminal 3 - API**:
```bash
python api.py
# Or use uvicorn directly:
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Usage

### Submit Content for Moderation

```bash
curl -X POST http://localhost:8000/moderate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test post",
    "content_type": "text",
    "user_id": "user123",
    "metadata": {}
  }'
```

Response:
```json
{
  "content_id": "uuid-here",
  "status": "queued",
  "message": "Content submitted for moderation"
}
```

### Check Moderation Status

```bash
curl http://localhost:8000/status/{content_id}
```

Response:
```json
{
  "content_id": "uuid",
  "severity": 0.85,
  "action": "suspend",
  "rationale": "Content suspended due to high severity (0.85). Issues: toxic language, spam indicators",
  "detected_issues": ["toxic language", "spam indicators"],
  "language": "en",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Submit Appeal

```bash
curl -X POST http://localhost:8000/appeal \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "uuid",
    "user_id": "user123",
    "appeal_reason": "This was taken out of context",
    "additional_context": "I was quoting someone else"
  }'
```

### Moderator Review

```bash
curl -X POST "http://localhost:8000/moderator/review/{content_id}?action=approve&notes=Reviewed manually&moderator_id=mod123"
```

## 🔍 How Moderation Works

### Decision Flow

```
Content → Language Detection → Content Analysis → Spam Check → 
Severity Calculation → Human Review? → Final Decision
```

### Severity Thresholds

| Severity | Action | Description |
|----------|--------|-------------|
| ≥ 0.8 | **SUSPEND** | Immediate suspension |
| ≥ 0.6 | **FLAG** | Flagged for review |
| ≥ 0.5 | **REVIEW** | Requires human review |
| < 0.5 | **APPROVE** | Content approved |

### Detection Categories

1. **Toxicity**: Hate speech, insults, threats
2. **Spam**: Repetitive content, commercial spam, burst posting
3. **Sarcasm**: Ambiguous or borderline sarcastic content
4. **Misinformation**: Potentially false information (with LLM)

### Example Decisions

#### 1. Toxic Post → Suspension
**Input**: "I hate you, you're stupid and should die"

**Decision**:
```json
{
  "severity": 0.9,
  "action": "suspend",
  "rationale": "Content suspended due to high severity (0.90). Issues: toxic language",
  "detected_issues": ["toxic language"]
}
```

#### 2. Spam Burst → Suspension
**Input**: "Buy now! Click here!" (5th post in 60 seconds)

**Decision**:
```json
{
  "severity": 1.0,
  "action": "suspend",
  "rationale": "Spam burst detected. User exceeded post limit.",
  "detected_issues": ["spam indicators", "spam burst detected"]
}
```

#### 3. Sarcasm Borderline → Human Review
**Input**: "Yeah right, that's totally what happened, sure"

**Decision**:
```json
{
  "severity": 0.65,
  "action": "review",
  "rationale": "Content requires manual review. Flagged for human review due to borderline severity",
  "detected_issues": ["possible sarcasm"],
  "requires_human_review": true
}
```

#### 4. Appeal → Moderator Modifies
**Original**: severity 0.75, action: flag
**Appeal**: "This was a quote from a book"
**New Decision**: severity 0.4, action: approve

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_moderation.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Test Cases Covered

- ✅ Toxic post detection and suspension
- ✅ Spam burst detection and suspension
- ✅ Sarcasm detection and human review routing
- ✅ Appeal processing
- ✅ Clean content approval
- ✅ Multiple issue detection
- ✅ API endpoints (submit, status, appeal)

## 🔧 Adding New Moderation Policies

### 1. Add Policy to Config

Edit `config.py`:

```python
MODERATION_POLICIES["profanity"] = {
    "threshold": 0.7,
    "action": "flag",
    "description": "Profane language"
}
```

### 2. Update Analysis Logic

Edit `moderation_graph.py` in `analyze_content`:

```python
def _rule_based_analysis(self, state: WorkflowState) -> Dict[str, Any]:
    # ...existing code...
    
    # Add profanity detection
    profanity_words = ["word1", "word2", "word3"]
    profanity_score = sum(1 for word in profanity_words if word in content) / 10
    if profanity_score > 0:
        detected_issues.append("profanity")
    
    return {
        # ...existing scores...
        "profanity_score": profanity_score,
        # ...
    }
```

### 3. Update Severity Calculation

```python
def calculate_severity(self, state: WorkflowState) -> Dict[str, Any]:
    severity = max(
        state.toxicity_score,
        state.spam_score,
        state.profanity_score * 0.9,  # Add new score
        state.sarcasm_score * 0.8
    )
    return {"severity": severity}
```

## 🎁 Bonus Features

### Multi-Language Detection

Automatically enabled. Detects content language using `langdetect`:

```python
from models import WorkflowState
state = WorkflowState(
    content="Bonjour le monde",
    # ...
)
# Result: language = "fr"
```

### Image Moderation (Placeholder)

```python
from image_moderation import ImageModerator

moderator = ImageModerator()
moderator.enable_moderation(api_key="your_key")

with open("image.jpg", "rb") as f:
    result = moderator.analyze_image(f.read())
    
print(result["severity"])
print(result["detected_issues"])
```

**Production Integration**: Replace placeholder with AWS Rekognition, Google Vision, or Azure Content Moderator.

### Real-Time Stream Processor

```bash
# Run stream processor
python stream_processor.py
```

Processes content from Redis Streams for real-time moderation at scale.

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### User Statistics

```bash
curl http://localhost:8000/stats/user/{user_id}
```

## 🐛 Troubleshooting

### Redis Connection Failed
```
ERROR: Cannot connect to Redis
```
**Solution**: Ensure Redis is running (`redis-server` or Docker)

### Worker Not Processing
- Check Redis connection
- Verify worker is running
- Check worker logs for errors

### API Key Issues
- Set `ANTHROPIC_API_KEY` environment variable
- System falls back to rule-based analysis without key

## 📚 Project Structure

```
assignmentintership/
├── api.py                  # FastAPI application
├── worker.py               # Background worker
├── moderation_graph.py     # LangGraph workflow
├── models.py               # Pydantic models
├── config.py               # Configuration
├── redis_client.py         # Redis operations
├── image_moderation.py     # Image moderation (bonus)
├── stream_processor.py     # Real-time processor (bonus)
├── requirements.txt        # Dependencies
├── README.md              # This file
└── tests/
    ├── __init__.py
    ├── test_moderation.py  # Workflow tests
    └── test_api.py         # API tests
```

## 🤝 Contributing

1. Add new moderation policies in `config.py`
2. Extend workflow nodes in `moderation_graph.py`
3. Add tests for new features
4. Update documentation

## 📄 License

MIT License - feel free to use in your projects!

## 🙏 Acknowledgments

- Built with LangGraph for workflow orchestration
- Powered by Claude Sonnet 4.5 for AI analysis
- FastAPI for high-performance API
- Redis for reliable message queuing

---

**Questions?** Check the code comments or run tests for examples.

**Production Ready**: This system includes error handling, fallbacks, and comprehensive testing.#   L a n g G r a p h - C o n t e n t - M o d e r a t i o n - S y s t e m  
 