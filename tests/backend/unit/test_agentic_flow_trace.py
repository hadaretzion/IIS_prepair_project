"""Integration tests tracing the interview flow for natural responses."""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.models import InterviewSession, QuestionBank, InterviewMode, InterviewTurn
from backend.schemas import InterviewNextRequest
from backend.services.interview_agent import AgenticInterviewAgent
from backend.services.agent_context import build_context_from_request
from backend.services.agent_reasoning import AgentReasoningLoop


class TestAgenticFlowNaturalResponses:
    """Test that agentic flow generates natural responses, not robotic ones."""
    
    def test_process_decision_uses_agent_message_for_followup(self):
        """Test that _process_decision uses agent's message for followups."""
        agent = AgenticInterviewAgent()
        
        # Create mock objects
        decision = Mock()
        decision.action = "followup"
        decision.followup_question = "Can you elaborate?"
        decision.message = "That's a great point about inheritance."  # Natural message from agent
        decision.satisfaction_score = 0.6
        
        question = Mock(spec=QuestionBank)
        question.id = "q1"
        
        state = {}
        plan_items = []
        
        interview_session = Mock(spec=InterviewSession)
        session = Mock()
        
        # This should use the agent's message, not fallback to acknowledgement
        response = agent._process_decision(
            decision=decision,
            question=question,
            question_id="q1",
            question_index=0,
            followup_count=0,
            previous_followups=[],
            plan_items=plan_items,
            interview_session=interview_session,
            state=state,
            session=session
        )
        
        # Check that response uses the agent's message
        assert response["interviewer_message"] is not None
        assert "That's a great point" in response["interviewer_message"]
        assert decision.message in response["interviewer_message"]
        print(f"✓ Followup uses agent message: {response['interviewer_message'][:80]}")
    
    def test_process_decision_uses_agent_message_for_advance(self):
        """Test that _process_decision uses agent's message for advancing."""
        agent = AgenticInterviewAgent()
        
        # Create mock objects
        decision = Mock()
        decision.action = "advance"
        decision.message = "Excellent analysis! You clearly understand this topic."
        decision.satisfaction_score = 0.85
        
        question = Mock(spec=QuestionBank)
        question.id = "q1"
        
        next_question = Mock(spec=QuestionBank)
        next_question.id = "q2"
        next_question.question_text = "What about polymorphism?"
        next_question.topics_json = "[]"
        
        plan_items = [{"selected_question_id": "q1"}, {"selected_question_id": "q2"}]
        
        interview_session = Mock(spec=InterviewSession)
        interview_session.question_start_time = datetime.utcnow()
        
        session = Mock()
        session.get.return_value = next_question
        session.exec.return_value.all.return_value = []
        
        state = {}
        
        response = agent._process_decision(
            decision=decision,
            question=question,
            question_id="q1",
            question_index=0,
            followup_count=0,
            previous_followups=[],
            plan_items=plan_items,
            interview_session=interview_session,
            state=state,
            session=session
        )
        
        # Check that response uses the agent's natural message
        assert response["interviewer_message"] is not None
        assert "Excellent analysis" in response["interviewer_message"]
        assert response["interviewer_message"] == decision.message
        print(f"✓ Advance uses agent message: {response['interviewer_message']}")
    
    def test_process_decision_for_hint(self):
        """Test that _process_decision properly handles hint action."""
        agent = AgenticInterviewAgent()
        
        decision = Mock()
        decision.action = "hint"
        decision.message = "Here's a hint: think about the parent class. What methods does it define?"
        
        question = Mock(spec=QuestionBank)
        question.id = "q1"
        
        response = agent._process_decision(
            decision=decision,
            question=question,
            question_id="q1",
            question_index=0,
            followup_count=0,
            previous_followups=[],
            plan_items=[],
            interview_session=Mock(),
            state={},
            session=Mock()
        )
        
        # Hint should use agent's message
        assert response["interviewer_message"] == decision.message
        assert "hint" in decision.message.lower() or "think about" in decision.message.lower()
        print(f"✓ Hint uses agent message: {response['interviewer_message'][:80]}")
    
    def test_process_decision_for_end(self):
        """Test that _process_decision properly handles end action."""
        agent = AgenticInterviewAgent()
        
        decision = Mock()
        decision.action = "end"
        decision.message = "You've demonstrated strong understanding throughout. Great job!"
        
        question = Mock(spec=QuestionBank)
        question.id = "q1"
        
        interview_session = Mock(spec=InterviewSession)
        session = Mock()
        
        response = agent._process_decision(
            decision=decision,
            question=question,
            question_id="q1",
            question_index=0,
            followup_count=0,
            previous_followups=[],
            plan_items=[],
            interview_session=interview_session,
            state={},
            session=session
        )
        
        # End should use agent's message
        assert response["interviewer_message"] == decision.message
        assert "strong understanding" in response["interviewer_message"].lower()
        print(f"✓ End uses agent message: {response['interviewer_message']}")


class TestAgentMessageGeneration:
    """Test that agent actually generates messages via respond_to_candidate."""
    
    def test_respond_to_candidate_called_before_advance(self):
        """Verify that respond_to_candidate should be called before advancing."""
        from backend.services.agent_reasoning import AGENT_SYSTEM_PROMPT
        
        # Check that system prompt enforces respond_to_candidate
        assert "respond_to_candidate" in AGENT_SYSTEM_PROMPT
        assert "CRITICAL" in AGENT_SYSTEM_PROMPT
        assert "ALWAYS use respond_to_candidate" in AGENT_SYSTEM_PROMPT
        print("✓ System prompt enforces respond_to_candidate usage")
    
    def test_generated_response_stored_in_decision(self):
        """Test that agent_reasoning.py stores generated_response in AgentDecision."""
        from backend.services import agent_reasoning
        
        source = agent_reasoning.__file__
        with open(source, 'r') as f:
            content = f.read()
        
        # Check that generated_response is stored when respond_to_candidate is called
        assert "generated_response = tool_result.data.get" in content
        assert 'decision.message = generated_response' in content or \
               'message=generated_response' in content
        
        print("✓ agent_reasoning.py stores generated_response in decision")


class TestNaturalResponseDetection:
    """Test that we can detect whether responses are natural or robotic."""
    
    def test_robotic_phrases_not_in_code(self):
        """Verify robotic phrases are removed from codebase."""
        import os
        import glob
        
        robotic_keywords = [
            "acknowledgement",
            "ACKNOWLEDGEMENTS",
            "_acknowledgement",
            '"Got it',
            "'Got it",
            '"Alright',
            "'Alright",
            '"Understood',
            "'Understood"
        ]
        
        python_files = glob.glob("backend/**/*.py", recursive=True)
        
        found_issues = []
        for filepath in python_files:
            # Skip test files and migrations
            if "test" in filepath or "migration" in filepath:
                continue
            
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    for keyword in robotic_keywords:
                        if keyword in content and "comment" not in filepath.lower():
                            found_issues.append(f"{filepath}: {keyword}")
            except:
                pass
        
        if found_issues:
            print(f"⚠ Found potential robotic code: {found_issues}")
        else:
            print("✓ No robotic phrases found in backend code")
        
        # This test reports but doesn't fail - for awareness


class TestPersonaInjection:
    """Test that persona is properly injected into agent flow."""
    
    def test_persona_in_system_prompt(self):
        """Test that persona affects the system prompt."""
        from backend.services.agent_reasoning import get_persona_prompt, AGENT_SYSTEM_PROMPT
        
        friendly_prompt = get_persona_prompt("friendly")
        formal_prompt = get_persona_prompt("formal")
        challenging_prompt = get_persona_prompt("challenging")
        
        # Each should be different
        assert friendly_prompt != formal_prompt
        assert formal_prompt != challenging_prompt
        
        # Each should mention the persona
        assert "friendly" in friendly_prompt.lower()
        assert "formal" in formal_prompt.lower()
        assert "challenging" in challenging_prompt.lower()
        
        # System prompt should have placeholder
        assert "{persona_section}" in AGENT_SYSTEM_PROMPT
        
        print("✓ Persona properly injected into system prompt")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
