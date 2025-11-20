# Testing Guide - Content Moderation System
<!-- CHATGPT suggested testing workflow  -->
## 🚀 Quick Start Testing

### Option 1: Test Workflow Only (No Setup Required)

Test the core moderation logic without starting any services:

```bash
python quick_test.py
```

**What it does:**
- Tests the LangGraph workflow directly
- No Redis/API/Worker needed
- Shows toxic, spam, sarcasm, and clean content handling
- Takes ~5 seconds

**Expected Output:**
```
Test 1: Toxic Content
   Severity: 0.70 (expected: > 0.5)
   Action: flag (expected: suspend or flag)
   ✅ PASS
```

---

### Option 2: Full System Test (Complete Setup)

Test the entire system with API, Worker, and Redis:

#### Step 1: Start Services (3 separate terminals)

**Terminal 1 - Redis:**
```bash
redis-server
# Or on Windows with Docker:
docker run -d -p 6379:6379 redis:latest
```

**Terminal 2 - Worker:**
```bash
python worker.py
```

**Expected Output:**
```
Starting moderation worker...
Using rule-based analysis (set ANTHROPIC_API_KEY for LLM analysis)
Worker ready. Waiting for content...
```

**Terminal 3 - API:**
```bash
python api.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Step 2: Run Demo Tests

**Terminal 4 - Demo:**
```bash
python demo.py
```

**What it does:**
- Submits 5 different test cases
- Checks processing results
- Tests appeal process
- Validates all scenarios

**Expected Output:**
```
TEST 1: Toxic Content → Suspension
📝 Submitting: "I hate you, you're stupid and should die"
✅ Submitted successfully! Content ID: abc-123-def
✅ Moderation Complete!
   Severity: 0.70
   Action: flag
   Issues: toxic language
✅ TEST 1 PASSED: Toxic content handled correctly
```

---

## 🧪 Manual Testing via API

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 2. Submit Toxic Content

```bash
curl -X POST http://localhost:8000/moderate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I hate you, you are stupid",
    "content_type": "text",
    "user_id": "user123"
  }'
```

**Expected:**
```json
{
  "content_id": "uuid-here",
  "status": "queued",
  "message": "Content submitted for moderation"
}
```

### 3. Check Status (wait 3-5 seconds)

```bash
curl http://localhost:8000/status/{content_id}
```

**Expected:**
```json
{
  "content_id": "uuid",
  "severity": 0.70,
  "action": "flag",
  "rationale": "Content flagged for review...",
  "detected_issues": ["toxic language"],
  "language": "en"
}
```

### 4. Submit Spam

```bash
curl -X POST http://localhost:8000/moderate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Buy now! Click here! Free money!!!",
    "content_type": "text",
    "user_id": "user456"
  }'
```

### 5. Test Spam Burst (run 6 times quickly)

```bash
for i in {1..6}; do
  curl -X POST http://localhost:8000/moderate \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"Spam post $i\", \"user_id\": \"spammer1\"}"
done
```

### 6. Submit Appeal

```bash
curl -X POST http://localhost:8000/appeal \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "uuid-from-step-2",
    "user_id": "user123",
    "appeal_reason": "This was taken out of context"
  }'
```

---

## 🔍 Verify Results

### Check Redis Directly

```bash
redis-cli

# List all keys
KEYS *

# Get a specific result
GET result:your-content-id

# Check queue length
LLEN content_moderation_queue

# Check user post count
GET user_posts:user123
```

### Check Worker Logs

Look for processing messages:
```
Processing content: abc-123-def
Completed: abc-123-def - Action: flag
```

### Interactive API Documentation

Open browser: http://localhost:8000/docs

- Try all endpoints interactively
- See request/response schemas
- Test different scenarios

---

## 📊 Expected Test Results

### Toxic Content
- **Input:** "I hate you, stupid idiot"
- **Expected Severity:** > 0.3 (rule-based) or > 0.7 (with LLM)
- **Expected Action:** flag, suspend, or review
- **Expected Issues:** toxic language

### Spam Content
- **Input:** "Buy now! Click here! Free money!"
- **Expected Severity:** > 0.4 (rule-based) or > 0.6 (with LLM)
- **Expected Action:** flag or suspend
- **Expected Issues:** spam indicators

### Sarcasm
- **Input:** "Yeah right, that's totally what happened"
- **Expected Severity:** 0.3-0.7
- **Expected Action:** review, flag, or approve
- **Expected Issues:** possible sarcasm (may not detect without LLM)

### Clean Content
- **Input:** "This is a nice day"
- **Expected Severity:** < 0.5
- **Expected Action:** approve
- **Expected Issues:** []

### Spam Burst
- **Input:** 6 posts in 60 seconds
- **Expected Severity:** 0.8-1.0
- **Expected Action:** suspend or flag
- **Expected Issues:** spam burst detected, spam indicators

---

## ⚠️ Important Notes

### Rule-Based vs LLM Analysis

**Without ANTHROPIC_API_KEY (Rule-Based):**
- Severity scores may be lower
- Detection is based on keyword matching
- Sarcasm detection is basic
- Some nuanced content may not be caught

**With ANTHROPIC_API_KEY (LLM Analysis):**
- More accurate severity scores
- Better context understanding
- Advanced sarcasm detection
- Handles nuanced content

### Expected Score Ranges

| Content Type | Rule-Based Severity | LLM Severity |
|--------------|-------------------|--------------|
| Toxic | 0.3-0.8 | 0.7-0.95 |
| Spam | 0.4-0.8 | 0.6-0.9 |
| Sarcasm | 0.2-0.6 | 0.5-0.8 |
| Clean | 0.0-0.2 | 0.0-0.3 |

---

## 🧪 Run Automated Tests

### All Tests

```bash
pytest tests/ -v
```

**Expected Output:**
```
tests/test_moderation.py::test_toxic_content_suspension PASSED
tests/test_moderation.py::test_spam_burst_suspension PASSED
tests/test_moderation.py::test_sarcasm_borderline_review PASSED
tests/test_moderation.py::test_clean_content_approval PASSED
tests/test_api.py::test_health_check PASSED
```

### Specific Test File

```bash
pytest tests/test_moderation.py -v
```

### With Coverage

```bash
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

---

## 🐛 Troubleshooting

### Issue: "Cannot connect to API"

**Solution:**
1. Check API is running: `curl http://localhost:8000/health`
2. Check port not in use: `netstat -an | grep 8000`
3. Restart API: `python api.py`

### Issue: "Redis not connected"

**Solution:**
1. Check Redis running: `redis-cli ping` (should return PONG)
2. Start Redis: `redis-server`
3. Check connection: `python -c "import redis; r=redis.Redis(); print(r.ping())"`

### Issue: "Worker not processing"

**Solution:**
1. Check worker is running (should show "Worker ready")
2. Check Redis queue: `redis-cli LLEN content_moderation_queue`
3. Restart worker: `python worker.py`

### Issue: "Tests failing"

**Solution:**
1. Ensure all services running
2. Clear Redis: `redis-cli FLUSHDB`
3. Restart all services
4. Run tests again

### Issue: "Validation error for ModerationDecision"

**Error Message:**
```
1 validation error for ModerationDecision
status
  Input should be 'pending', 'processing', 'completed' or 'appealed'
```

**Solution:**
This was a bug in the worker where it passed invalid status values. It's now fixed.
- Restart the worker: `python worker.py`
- The worker will now use valid status values from the ModerationStatus enum

**Valid Status Values:**
- `pending`: Content waiting for review or initial processing
- `processing`: Content currently being analyzed
- `completed`: Moderation decision finalized
- `appealed`: User has submitted an appeal
- `review_required`: Requires human moderator review

### Issue: "Content stuck in processing"

**Solution:**
1. Check worker logs for errors
2. Restart worker to clear stuck jobs
3. Resubmit the content if needed
4. Check Redis queue: `redis-cli LLEN content_moderation_queue`

---

## 📈 Performance Validation

### Response Times

**Expected:**
- API submission: < 50ms
- Processing: 2-5 seconds (rule-based)
- Processing: 5-10 seconds (with LLM)
- Status check: < 10ms

### Measure Performance

```python
import time
import requests

start = time.time()
response = requests.post("http://localhost:8000/moderate", json={...})
print(f"Submission time: {time.time() - start:.3f}s")

content_id = response.json()["content_id"]
time.sleep(3)

start = time.time()
response = requests.get(f"http://localhost:8000/status/{content_id}")
print(f"Status check time: {time.time() - start:.3f}s")
```

---

## ✅ Validation Checklist

- [ ] Redis is running and connected
- [ ] Worker is processing content
- [ ] API responds to health check
- [ ] Toxic content gets flagged/suspended
- [ ] Spam burst is detected
- [ ] Sarcasm triggers review
- [ ] Clean content is approved
- [ ] Appeals can be submitted
- [ ] Moderator can override decisions
- [ ] All automated tests pass
- [ ] Performance is acceptable

---

## 🎯 Success Criteria

Your system is working correctly if:

1. ✅ All services start without errors
2. ✅ Health check returns "healthy"
3. ✅ Content submission returns content_id
4. ✅ Worker logs show processing messages
5. ✅ Status endpoint returns decisions
6. ✅ Severity scores match expectations
7. ✅ Actions match content type
8. ✅ All automated tests pass

---

## 📞 Next Steps After Validation

Once all tests pass:

1. **Monitor Logs:** Watch worker output for processing
2. **Test Edge Cases:** Try unusual content
3. **Performance Test:** Submit many items
4. **Add Policies:** Extend moderation rules
5. **Enable LLM:** Add ANTHROPIC_API_KEY for AI analysis

Ready to deploy! 🚀
