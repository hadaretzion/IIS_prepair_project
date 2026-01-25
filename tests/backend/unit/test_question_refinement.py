import pytest
from unittest.mock import patch, MagicMock
from backend.services.interview_agent import AgenticInterviewAgent

class TestQuestionRefinement:
    def setup_method(self):
        self.agent = AgenticInterviewAgent()

    @patch('backend.services.interview_agent.call_llm')
    def test_refine_english(self, mock_llm):
        mock_llm.return_value = "Refined Question?"
        
        result = self.agent._refine_and_translate("Original Question", "open", "english")
        
        assert result == "Refined Question?"
        mock_llm.assert_called_once()
        args = mock_llm.call_args[0]
        assert "Refine Interview Question" in args[1] # Check prompt contains instructions

    @patch('backend.services.interview_agent.call_llm')
    def test_refine_hebrew_translation(self, mock_llm):
        mock_llm.return_value = "Hebrew Question?"
        
        result = self.agent._refine_and_translate("Original Question", "open", "hebrew")
        
        assert result == "Hebrew Question?"
        mock_llm.assert_called_once()
        args = mock_llm.call_args[0]
        assert "Translate and Refine" in args[1]
        assert "Hebrew" in args[1]

    @patch('backend.services.interview_agent.call_llm')
    def test_refine_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = Exception("API Error")
        
        result = self.agent._refine_and_translate("Original Question", "open", "english")
        
        assert result == "Original Question"
