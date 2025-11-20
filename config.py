import os
from typing import Dict, Any

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Anthropic API Key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Moderation Policies
MODERATION_POLICIES: Dict[str, Any] = {
    "toxicity": {
        "threshold": 0.8,
        "action": "suspend",
        "description": "Toxic, hateful, or abusive content"
    },
    "spam": {
        "threshold": 0.7,
        "action": "suspend",
        "description": "Repetitive or commercial spam"
    },
    "sarcasm": {
        "threshold": 0.6,
        "action": "review",
        "description": "Borderline sarcastic or ambiguous content"
    },
    "misinformation": {
        "threshold": 0.75,
        "action": "flag",
        "description": "Potentially false or misleading information"
    }
}

# Severity Thresholds
SEVERITY_THRESHOLDS = {
    "suspend": 0.8,
    "flag": 0.6,
    "review": 0.5,
    "approve": 0.0
}

# Spam Detection Settings
SPAM_BURST_THRESHOLD = 5  # posts in time window
SPAM_TIME_WINDOW = 60  # seconds

# Queue Settings
CONTENT_QUEUE = "content_moderation_queue"
RESULT_QUEUE = "moderation_results"
