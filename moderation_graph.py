from langgraph.graph import StateGraph, END
from typing import Dict, Any
from models import WorkflowState, ModerationAction
from config import MODERATION_POLICIES, SEVERITY_THRESHOLDS, SPAM_BURST_THRESHOLD
import json
from datetime import datetime
import re

class ModerationWorkflow:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("detect_language", self.detect_language)
        workflow.add_node("analyze_content", self.analyze_content)
        workflow.add_node("check_spam", self.check_spam)
        workflow.add_node("calculate_severity", self.calculate_severity)
        workflow.add_node("make_decision", self.make_decision)
        workflow.add_node("human_review", self.human_review)
        
        # Set entry point
        workflow.set_entry_point("detect_language")
        
        # Add edges
        workflow.add_edge("detect_language", "analyze_content")
        workflow.add_edge("analyze_content", "check_spam")
        workflow.add_edge("check_spam", "calculate_severity")
        workflow.add_conditional_edges(
            "calculate_severity",
            self.should_review,
            {
                "review": "human_review",
                "decide": "make_decision"
            }
        )
        workflow.add_edge("human_review", "make_decision")
        workflow.add_edge("make_decision", END)
        
        return workflow.compile()
    
    def detect_language(self, state: WorkflowState) -> Dict[str, Any]:
        """Detect content language"""
        try:
            from langdetect import detect
            language = detect(state.content)
        except:
            language = "en"
        
        return {"language": language}
    
    def analyze_content(self, state: WorkflowState) -> Dict[str, Any]:
        """Analyze content using LLM for toxicity, spam, and sarcasm"""
        if not self.llm_client:
            # Fallback to rule-based analysis
            return self._rule_based_analysis(state)
        
        try:
            prompt = f"""Analyze the following content for moderation purposes. 
Rate each category from 0.0 to 1.0 and provide detected issues.

Content: "{state.content}"

Provide a JSON response with:
{{
    "toxicity_score": <float>,
    "spam_score": <float>,
    "sarcasm_score": <float>,
    "detected_issues": [<list of specific issues found>],
    "analysis": "<brief explanation>"
}}"""

            response = self.llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content_text = response.content[0].text
            result = json.loads(content_text)
            
            return {
                "toxicity_score": result.get("toxicity_score", 0.0),
                "spam_score": result.get("spam_score", 0.0),
                "sarcasm_score": result.get("sarcasm_score", 0.0),
                "detected_issues": result.get("detected_issues", []),
                "rationale": result.get("analysis", "")
            }
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._rule_based_analysis(state)
    
    def _rule_based_analysis(self, state: WorkflowState) -> Dict[str, Any]:
        """Fallback rule-based content analysis"""
        content = state.content.lower()
        detected_issues = []
        
        # Expanded toxicity keywords with weighted scoring
        toxic_keywords = {
            "hate": 0.3, "kill": 0.4, "die": 0.4, "death": 0.3,
            "stupid": 0.2, "idiot": 0.2, "dumb": 0.2, "moron": 0.2,
            "trash": 0.2, "garbage": 0.2, "worthless": 0.3,
            "worst": 0.1, "terrible": 0.1, "horrible": 0.2,
            "fuck": 0.3, "shit": 0.2, "damn": 0.1,
            "loser": 0.2, "pathetic": 0.2, "disgusting": 0.3
        }
        
        toxicity_score = 0.0
        for word, weight in toxic_keywords.items():
            if word in content:
                toxicity_score += weight
        
        # Cap at 1.0
        toxicity_score = min(toxicity_score, 1.0)
        
        if toxicity_score > 0.1:
            detected_issues.append("toxic language")
        
        # Spam detection
        spam_indicators = ["buy now", "click here", "free money", "win prize", "$$$", 
                          "limited offer", "act now", "discount", "www.", "http"]
        spam_score = sum(0.2 for indicator in spam_indicators if indicator in content)
        
        # Check for repetitive content
        words = content.split()
        if len(words) > 0:
            most_common_word = max(set(words), key=words.count) if words else ""
            word_repetition = words.count(most_common_word) / len(words) if len(words) > 0 else 0
            
            if word_repetition > 0.4:  # More than 40% same word
                spam_score = max(spam_score, 0.7)
        
        # Very short content is often spam
        if len(content) < 10 and len(content) > 0:
            spam_score = max(spam_score, 0.5)
        
        spam_score = min(spam_score, 1.0)
        
        if spam_score > 0.2:
            detected_issues.append("spam indicators")
        
        # Sarcasm detection (basic)
        sarcasm_indicators = {
            "yeah right": 0.3, "sure": 0.2, "totally": 0.2, 
            "obviously": 0.2, "lol": 0.1, "whatever": 0.2,
            "great job": 0.1, "well done": 0.1, "genius": 0.1
        }
        
        sarcasm_score = 0.0
        for phrase, weight in sarcasm_indicators.items():
            if phrase in content:
                sarcasm_score += weight
        
        sarcasm_score = min(sarcasm_score, 1.0)
        
        if sarcasm_score > 0.3:
            detected_issues.append("possible sarcasm")
        
        return {
            "toxicity_score": toxicity_score,
            "spam_score": spam_score,
            "sarcasm_score": sarcasm_score,
            "detected_issues": detected_issues,
            "rationale": f"Rule-based analysis detected: {', '.join(detected_issues) if detected_issues else 'no issues'}"
        }
    
    def check_spam(self, state: WorkflowState) -> Dict[str, Any]:
        """Check for spam burst patterns"""
        # In production, query Redis for user's recent post count
        # For now, use metadata
        recent_posts = state.metadata.get("recent_post_count", 0)
        
        if recent_posts >= SPAM_BURST_THRESHOLD:
            return {
                "spam_score": 1.0,
                "detected_issues": state.detected_issues + ["spam burst detected"]
            }
        
        return {}
    
    def calculate_severity(self, state: WorkflowState) -> Dict[str, Any]:
        """Calculate overall severity score"""
        severity = max(
            state.toxicity_score,
            state.spam_score,
            state.sarcasm_score * 0.8  # Weight sarcasm lower
        )
        
        return {"severity": severity}
    
    def should_review(self, state: Dict[str, Any]) -> str:
        """Determine if human review is needed"""
        # LangGraph passes dict, not WorkflowState object
        sarcasm_score = state.get("sarcasm_score", 0.0)
        severity = state.get("severity", 0.0)
        detected_issues = state.get("detected_issues", [])
        
        # Borderline sarcasm cases need review
        if (sarcasm_score > 0.5 and sarcasm_score < 0.8 and
            severity < SEVERITY_THRESHOLDS["suspend"]):
            return "review"
        
        # High severity but unclear intent
        if (severity > 0.7 and severity < 0.85 and
            len(detected_issues) > 2):
            return "review"
        
        return "decide"
    
    def human_review(self, state: WorkflowState) -> Dict[str, Any]:
        """Flag for human review"""
        rationale = state.rationale if isinstance(state, WorkflowState) else state.get("rationale", "")
        
        return {
            "requires_human_review": True,
            "action": ModerationAction.REVIEW,
            "rationale": rationale + " [Flagged for human review due to borderline severity or ambiguous content]"
        }
    
    def make_decision(self, state: WorkflowState) -> Dict[str, Any]:
        """Make final moderation decision"""
        # Handle both dict and WorkflowState
        if isinstance(state, dict):
            requires_human_review = state.get("requires_human_review", False)
            severity = state.get("severity", 0.0)
            rationale = state.get("rationale", "")
            detected_issues = state.get("detected_issues", [])
        else:
            requires_human_review = state.requires_human_review
            severity = state.severity
            rationale = state.rationale
            detected_issues = state.detected_issues
        
        if requires_human_review:
            return {}  # Already set in human_review
        
        if severity >= SEVERITY_THRESHOLDS["suspend"]:
            action = ModerationAction.SUSPEND
        elif severity >= SEVERITY_THRESHOLDS["flag"]:
            action = ModerationAction.FLAG
        elif severity >= SEVERITY_THRESHOLDS["review"]:
            action = ModerationAction.REVIEW
        else:
            action = ModerationAction.APPROVE
        
        if not rationale:
            # Create a temporary state-like object for rationale generation
            state_obj = type('StateObj', (), {
                'severity': severity,
                'detected_issues': detected_issues
            })()
            rationale = self._generate_rationale(state_obj, action)
        
        return {
            "action": action,
            "rationale": rationale
        }
    
    def _generate_rationale(self, state, action: ModerationAction) -> str:
        """Generate human-readable rationale"""
        severity = state.severity if hasattr(state, 'severity') else 0.0
        detected_issues = state.detected_issues if hasattr(state, 'detected_issues') else []
        
        issues = ", ".join(detected_issues) if detected_issues else "no significant issues"
        
        rationales = {
            ModerationAction.SUSPEND: f"Content suspended due to high severity ({severity:.2f}). Issues: {issues}",
            ModerationAction.FLAG: f"Content flagged for review. Severity: {severity:.2f}. Issues: {issues}",
            ModerationAction.REVIEW: f"Content requires manual review. Severity: {severity:.2f}. Issues: {issues}",
            ModerationAction.APPROVE: f"Content approved. Low severity ({severity:.2f}). {issues}"
        }
        
        return rationales.get(action, f"Moderation action: {action}")
    
    def process_content(self, state_dict: Dict[str, Any]) -> WorkflowState:
        """Process content through the workflow"""
        state = WorkflowState(**state_dict)
        result = self.graph.invoke(state.model_dump())
        return WorkflowState(**result)
    
    def process_appeal(self, state_dict: Dict[str, Any]) -> WorkflowState:
        """Process an appeal with additional context"""
        state_dict["is_appeal"] = True
        state = WorkflowState(**state_dict)
        
        # Re-analyze with appeal context
        result = self.graph.invoke(state.model_dump())
        return WorkflowState(**result)
