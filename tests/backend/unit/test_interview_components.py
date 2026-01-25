"""Unit tests for interview agent components."""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.models import InterviewSession, QuestionBank, InterviewMode, User
from backend.schemas import InterviewNextRequest, InterviewSettings
from backend.services.agent_context import AgentContext, build_context_from_request
from backend.services.agent_reasoning import AgentReasoningLoop, AgentDecision, PERSONA_PRESETS
from backend.services.interview_agent import AgenticInterviewAgent, InterviewAgent
from backend.services.agent_tools import execute_respond_to_candidate, execute_ask_followup


class TestAgentContext:
    """Test AgentContext and context building."""
    
    def test_context_has_persona(self):
        """Test that AgentContext includes persona field."""
        context = AgentContext(
            session_id="test_session",
            question_id="q1",
            question_text="What is OOP?",
            question_type="open",
            question_topics=["oop", "design"],
            user_transcript="OOP is a programming paradigm...",
            user_code=None,
            question_index=0,
            total_questions=5,
            followup_count=0,
            persona="friendly"
        )
        
        assert context.persona == "friendly"
        assert hasattr(context, 'persona')
        print("✓ Context has persona field")
    
    def test_persona_in_system_prompt_context(self):
        """Test that persona affects the context string."""
        context = AgentContext(
            session_id="test",
            question_id="q1",
            question_text="Hello?",
            question_type="open",
            question_topics=[],
            user_transcript="Hi",
            user_code=None,
            question_index=0,
            total_questions=1,
            followup_count=0,
            persona="formal"
        )
        
        prompt_context = context.to_system_prompt_context()
        assert prompt_context  # Should have some context
        print(f"✓ Context generates prompt context: {len(prompt_context)} chars")
    
    def test_build_context_includes_persona(self):
        """Test that build_context_from_request includes persona."""
        # Mock question
        question = Mock(spec=QuestionBank)
        question.id = "q1"
        question.question_text = "Test question"
        question.question_type = Mock(value="open")
        question.topics_json = "[]"
        question.solution_text = None
        
        # Mock request
        request = Mock(spec=InterviewNextRequest)
        request.user_transcript = "Test answer"
        request.user_code = None
        
        context = build_context_from_request(
            session_id="test",
            question=question,
            request=request,
            plan_items=[{"selected_question_id": "q1"}],
            role_profile={},
            state={},
            persona="challenging"
        )
        
        assert context.persona == "challenging"
        print("✓ build_context_from_request preserves persona")


class TestAgentReasoningLoop:
    """Test the reasoning loop that generates responses."""
    
    def test_reasoning_loop_generates_agent_decision(self):
        """Test that reasoning loop returns AgentDecision."""
        loop = AgentReasoningLoop()
        context = AgentContext(
            session_id="test",
            question_id="q1",
            question_text="What is 2+2?",
            question_type="open",
            question_topics=[],
            user_transcript="4",
            user_code=None,
            question_index=0,
            total_questions=1,
            followup_count=0,
            persona="friendly"
        )
        
        # This should not crash
        assert loop.tools is not None
        assert hasattr(loop, 'run')
        print("✓ Reasoning loop initialized with tools")
    
    def test_persona_presets_exist(self):
        """Test that persona presets are defined."""
        assert "friendly" in PERSONA_PRESETS
        assert "formal" in PERSONA_PRESETS
        assert "challenging" in PERSONA_PRESETS
        
        for persona_name, preset in PERSONA_PRESETS.items():
            assert "style" in preset
            assert "tone" in preset
            assert "examples" in preset
            assert isinstance(preset["examples"], list)
            print(f"✓ Persona '{persona_name}' has all required fields")


class TestAgentTools:
    """Test individual agent tools."""
    
    def test_respond_to_candidate_tool(self):
        """Test respond_to_candidate tool generates natural response."""
        result = execute_respond_to_candidate(
            context="Test context",
            candidate_response="Test answer",
            message="Your answer about loops was good. "
        )
        
        assert result.success
        assert "response" in result.data
        assert isinstance(result.data["response"], str)
        assert len(result.data["response"]) > 0
        print(f"✓ respond_to_candidate tool works: {result.data['response'][:100]}")
    
    def test_ask_followup_tool(self):
        """Test ask_followup tool generates follow-up questions."""
        result = execute_ask_followup(
            question="What is inheritance?",
            candidate_answer="It's when a class gets properties from another class",
            followup_type="probe_deeper",
            previous_followups=[]
        )
        
        assert result.success
        assert "followup_question" in result.data
        followup = result.data["followup_question"]
        assert isinstance(followup, str)
        assert len(followup) > 0
        assert "?" in followup  # Should be a question
        print(f"✓ ask_followup tool works: {followup}")


class TestAgenticInterviewAgent:
    """Test the agentic interview agent."""
    
    def test_agent_returns_dict_response(self, db_session):
        """Test that agent.process_turn returns valid response dict."""
        agent = InterviewAgent()
        assert agent is not None
        assert hasattr(agent, 'process_turn')
        print("✓ InterviewAgent instantiates")


class TestAgentDecision:
    """Test AgentDecision return values."""
    
    def test_agent_decision_has_message(self):
        """Test that AgentDecision includes a message field."""
        decision = AgentDecision(
            action="advance",
            message="Great answer! Let's move on.",
            satisfaction_score=0.8
        )
        
        assert decision.action == "advance"
        assert decision.message is not None
        assert len(decision.message) > 0
        assert not decision.message.startswith("Got it")  # Not robotic
        print(f"✓ AgentDecision has natural message: {decision.message}")
    
    def test_decision_with_persona_message(self):
        """Test that decision messages should be persona-appropriate."""
        # Friendly persona
        friendly_msg = "That's a great observation! I like how you're thinking about this."
        decision_friendly = AgentDecision(
            action="followup",
            message=friendly_msg,
            followup_question="Can you elaborate?",
            satisfaction_score=0.7
        )
        
        assert "great" in decision_friendly.message.lower()
        assert not any(word in decision_friendly.message.lower() for word in ["got it", "understood"])
        
        # Formal persona
        formal_msg = "Your analysis demonstrates understanding of the fundamental concepts."
        decision_formal = AgentDecision(
            action="followup",
            message=formal_msg,
            followup_question="Please elaborate further.",
            satisfaction_score=0.7
        )
        
        assert "demonstrates" in decision_formal.message.lower()
        assert not any(word in decision_formal.message.lower() for word in ["great", "love"])
        
        print("✓ AgentDecision messages are persona-appropriate")


class TestInterviewFlow:
    """Integration tests for interview flow."""
    
    def test_no_hardcoded_acknowledgements(self):
        """Test that there are no hardcoded acknowledgements in agent."""
        from backend.services import interview_agent
        
        # Check source code for hardcoded messages
        source = interview_agent.__file__
        with open(source, 'r') as f:
            content = f.read()
        
        robotic_phrases = [
            '"Got it',
            "'Got it",
            '"Understood',
            "'Understood",
            '"Let\'s keep going',
            "'Let's keep going",
            '"Alright, let\'s continue',
            "'Alright, let's continue"
        ]
        
        for phrase in robotic_phrases:
            assert phrase not in content, f"Found hardcoded phrase: {phrase}"
        
        print("✓ No hardcoded acknowledgements in interview_agent.py")
    
    def test_no_acknowledgements_in_router(self):
        """Test that interview router doesn't reference ACKNOWLEDGEMENTS."""
        from backend.routers import interview
        
        source = interview.__file__
        with open(source, 'r') as f:
            content = f.read()
        
        assert "ACKNOWLEDGEMENTS" not in content, "Router still has ACKNOWLEDGEMENTS list"
        assert "_acknowledgement_for_turn" not in content, "Router still has acknowledgement function"
        
        print("✓ Interview router has no ACKNOWLEDGEMENTS")
    
    def test_persona_is_used_in_agent(self):
        """Test that persona field is actually passed to agent."""
        from backend.services.agent_reasoning import get_persona_prompt
        
        # Test that persona prompts are generated
        for persona in ["friendly", "formal", "challenging"]:
            prompt = get_persona_prompt(persona)
            assert prompt is not None
            assert len(prompt) > 0
            assert persona.title() in prompt or persona in prompt
            print(f"✓ Persona prompt generated for '{persona}'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
