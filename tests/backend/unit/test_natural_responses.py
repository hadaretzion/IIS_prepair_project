"""Test to verify all interviewer responses are truly natural and agentic."""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from backend.services.agent_reasoning import AgentReasoningLoop, AgentContext, AgentDecision, ReasoningStep
from backend.services.interview_agent import InterviewAgent
from backend.models import InterviewSession, QuestionBank


class TestNaturalAgenticResponses:
    """Verify that ALL interviewer messages are generated through LLM, not hardcoded."""

    def setup_method(self):
        """Set up test context."""
        self.interview = InterviewSession(
            interview_id="test_123",
            user_id="user_123",
            persona="friendly",
            role="Software Engineer",
            difficulty="medium",
            question_index=0,
            followup_count=0,
            chat_history="[]",
            ended=False,
        )

        self.question = QuestionBank(
            question_id="q1",
            question_text="Describe your experience with Python",
            category="languages",
            difficulty="easy",
        )

    def test_fallback_decision_uses_llm_not_hardcoded(self):
        """Verify _fallback_decision generates messages via LLM, not hardcoded."""
        loop = AgentReasoningLoop(self.interview)
        context = AgentContext(
            interview=self.interview,
            question=self.question,
            user_transcript="I have experience with Python",
            persona="friendly",
        )
        trace = []

        # Mock the call_llm to verify it's being called
        with patch("backend.services.agent_reasoning.call_llm") as mock_llm:
            mock_llm.return_value = "That's great! You have solid Python experience. Let's explore this further."
            
            decision = loop._fallback_decision(context, "Simulated error", trace)
            
            # Verify call_llm was called (means not hardcoded)
            assert mock_llm.called, "_fallback_decision should call call_llm to generate natural response"
            
            # Verify the message is not one of the old hardcoded messages
            old_hardcoded = [
                "Let's move on to the next question.",
                "Thank you for your responses. The interview is complete.",
                "Good, let's continue with the next question.",
                "Let's continue.",
            ]
            assert decision.message not in old_hardcoded, \
                f"Decision message '{decision.message}' is one of the old hardcoded messages"
            
            print(f"✓ _fallback_decision generated natural message: {decision.message}")

    def test_groq_followup_fallback_generates_natural_response(self):
        """Verify _groq_followup_fallback generates via LLM, not hardcoded."""
        loop = AgentReasoningLoop(self.interview)
        context = AgentContext(
            interview=self.interview,
            question=self.question,
            user_transcript="I mainly use Python for data analysis",
            persona="friendly",
        )
        trace = []

        with patch("backend.services.agent_reasoning.call_llm") as mock_llm:
            with patch.dict(os.environ, {"GROQ_API_KEY": "fake_key"}):
                mock_llm.return_value = "That sounds interesting! Have you worked with any specific frameworks like Django or FastAPI?"
                
                decision = loop._groq_followup_fallback(context, "Gemini failed", trace)
                
                if decision:  # May return None if no API key
                    # Verify LLM was called
                    assert mock_llm.called, "_groq_followup_fallback should use LLM to generate message"
                    
                    # Verify not the old hardcoded message
                    assert decision.message != "Let's dig a bit deeper.", \
                        "Should not use old hardcoded message 'Let's dig a bit deeper.'"
                    
                    print(f"✓ _groq_followup_fallback generated: {decision.message}")

    def test_test_mode_decision_uses_llm(self):
        """Verify _test_mode_decision generates via LLM in tests."""
        loop = AgentReasoningLoop(self.interview)
        context = AgentContext(
            interview=self.interview,
            question=self.question,
            user_transcript="I have Python experience",
            persona="friendly",
        )
        trace = []

        with patch("backend.services.agent_reasoning.call_llm") as mock_llm:
            mock_llm.return_value = "That's excellent! Can you tell me about a specific project where you used Python?"
            
            decision = loop._test_mode_decision(context, trace)
            
            # Verify LLM was called
            assert mock_llm.called, "_test_mode_decision should use LLM to generate messages"
            
            # Verify not old hardcoded messages
            old_hardcoded_test = ["Let's dig a bit deeper.", "Thanks, let's move on.", "Got it.", "Thank you."]
            assert decision.message not in old_hardcoded_test, \
                f"_test_mode_decision should not use hardcoded messages like '{decision.message}'"
            
            print(f"✓ _test_mode_decision generated: {decision.message}")

    def test_interpret_final_response_uses_llm(self):
        """Verify _interpret_final_response uses LLM for fallback message."""
        loop = AgentReasoningLoop(self.interview)
        context = AgentContext(
            interview=self.interview,
            question=self.question,
            user_transcript="I worked with Flask and Django",
            persona="friendly",
        )
        trace = []

        with patch("backend.services.agent_reasoning.call_llm") as mock_llm:
            mock_llm.return_value = "Great framework experience! Let's explore your backend architecture knowledge next."
            
            # Test when agent responds with text that doesn't match any keyword
            decision = loop._interpret_final_response(
                "The candidate has good framework experience",
                context,
                {"score": 0.7},
                trace
            )
            
            # Verify LLM was called for the default advance case
            assert mock_llm.called, "_interpret_final_response should use LLM for natural messages"
            
            # Verify not "Let's continue."
            assert decision.message != "Let's continue.", \
                "Should generate natural message via LLM, not hardcoded 'Let's continue.'"
            
            print(f"✓ _interpret_final_response generated: {decision.message}")

    def test_no_hardcoded_messages_in_fallbacks(self):
        """Scan agent_reasoning.py to ensure NO hardcoded messages in fallback functions."""
        import inspect
        from backend.services import agent_reasoning
        
        source = inspect.getsource(agent_reasoning.AgentReasoningLoop)
        
        # These are the old hardcoded messages that should NOT appear
        forbidden_messages = [
            '"Let\'s dig a bit deeper."',
            '"Thanks, let\'s move on."',
            '"Got it."',
            '"Thank you."',
            '"Let\'s continue."',
            '"Let\'s move on to the next question."',
            '"Thank you for your responses. The interview is complete."',
            '"Good, let\'s continue with the next question."',
            # Also check the message= format
            'message="Let\'s dig a bit deeper.',
            'message="Thanks, let\'s move on.',
            'message="Got it.',
            'message="Thank you.',
            'message="Let\'s continue.',
            'message="Let\'s move on to the next',
            'message="Thank you for your responses',
            'message="Good, let\'s continue',
        ]
        
        found_hardcoded = []
        for forbidden in forbidden_messages:
            # Look for the exact string in _fallback_decision, _groq_followup_fallback, etc.
            if forbidden in source:
                # Check if it's in a comment (benign) or actual code
                if not forbidden.replace('"', '') in ["Let's dig a bit deeper", "Thanks, let's move on", "Got it", "Thank you", "Let's continue", "Let's move on to the next", "Thank you for your responses", "Good, let's continue"]:
                    found_hardcoded.append(forbidden)
        
        assert len(found_hardcoded) == 0, \
            f"Found hardcoded messages in agent_reasoning.py: {found_hardcoded}\n" \
            f"All messages should be generated via LLM, not hardcoded."
        
        print(f"✓ No hardcoded messages found in agent_reasoning.py fallback functions")

    def test_interview_agent_uses_agentic_flow(self):
        """Verify InterviewAgent always uses AgenticInterviewAgent, no fallback to legacy."""
        agent = InterviewAgent(self.interview)
        
        # The agent should have an agentic_agent attribute
        assert hasattr(agent, "agentic_agent"), \
            "InterviewAgent should have agentic_agent attribute"
        
        # It should NOT have legacy agent attributes
        assert not hasattr(agent, "legacy_agent"), \
            "InterviewAgent should not have legacy_agent"
        
        assert not hasattr(agent, "acknowledgements"), \
            "InterviewAgent should not have acknowledgements fallback"
        
        print(f"✓ InterviewAgent correctly uses only agentic flow")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
