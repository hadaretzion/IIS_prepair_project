"""Agent tools for the interview agent.

Each tool has:
1. A schema definition (for Gemini function calling)
2. An implementation function
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from backend.services.llm_client import call_llm
from backend.services.agent_guardrails import filter_question


# =============================================================================
# Tool Schemas (for Gemini function calling)
# =============================================================================

TOOL_SCHEMAS = [
    {
        "name": "respond_to_candidate",
        "description": "Generate a natural, conversational response to the candidate. Use this to acknowledge their answer, provide feedback, and transition to the next topic. This makes you sound like a real interviewer, not a robot.",
        "parameters": {
            "type": "object",
            "properties": {
                "response_type": {
                    "type": "string",
                    "description": "Type of response: acknowledge (brief response before followup), transition (moving to next question), feedback (commenting on their answer), clarify (asking them to explain more)",
                    "enum": ["acknowledge", "transition", "feedback", "clarify"]
                },
                "candidate_said": {
                    "type": "string",
                    "description": "Brief summary of what the candidate said (to reference naturally)"
                },
                "tone": {
                    "type": "string",
                    "description": "Tone to use: encouraging, neutral, probing",
                    "enum": ["encouraging", "neutral", "probing"]
                },
                "next_topic": {
                    "type": "string",
                    "description": "If transitioning, what topic/question comes next"
                }
            },
            "required": ["response_type", "candidate_said", "tone"]
        }
    },
    {
        "name": "analyze_answer",
        "description": "Analyze the candidate's verbal/written answer for completeness, correctness, and clarity. Returns score, strengths, gaps, and whether follow-up is needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer_text": {
                    "type": "string",
                    "description": "The candidate's answer text to analyze"
                },
                "question_context": {
                    "type": "string",
                    "description": "The original question being answered"
                },
                "role_level": {
                    "type": "string",
                    "description": "Expected role level (junior, mid, senior)",
                    "enum": ["junior", "mid", "senior"]
                }
            },
            "required": ["answer_text", "question_context"]
        }
    },
    {
        "name": "evaluate_code",
        "description": "Evaluate code quality, correctness, efficiency, and style. Use this when the candidate provides code.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The candidate's code to evaluate"
                },
                "question": {
                    "type": "string",
                    "description": "The coding question/problem"
                },
                "reference_solution": {
                    "type": "string",
                    "description": "Optional reference solution to compare against"
                }
            },
            "required": ["code", "question"]
        }
    },
    {
        "name": "ask_followup",
        "description": "Generate and ask a follow-up question to clarify, probe deeper, or challenge the candidate's answer. Use when the answer is incomplete or you want to explore further.",
        "parameters": {
            "type": "object",
            "properties": {
                "followup_type": {
                    "type": "string",
                    "description": "Type of follow-up: clarify (unclear answer), probe_deeper (explore further), challenge (test understanding)",
                    "enum": ["clarify", "probe_deeper", "challenge"]
                },
                "focus_area": {
                    "type": "string",
                    "description": "The specific topic or gap to address"
                },
                "context": {
                    "type": "string",
                    "description": "Context about the original question and answer"
                }
            },
            "required": ["followup_type", "focus_area", "context"]
        }
    },
    {
        "name": "give_hint",
        "description": "Provide a helpful hint when the candidate appears stuck or confused. Use sparingly to maintain interview integrity.",
        "parameters": {
            "type": "object",
            "properties": {
                "hint_level": {
                    "type": "string",
                    "description": "How direct the hint should be: gentle (vague nudge), moderate (direction), direct (specific pointer)",
                    "enum": ["gentle", "moderate", "direct"]
                },
                "topic_area": {
                    "type": "string",
                    "description": "The area where the candidate needs help"
                },
                "question_context": {
                    "type": "string",
                    "description": "The current question context"
                }
            },
            "required": ["hint_level", "topic_area", "question_context"]
        }
    },
    {
        "name": "advance_to_next",
        "description": "Move to the next question in the interview. Use when satisfied with the answer or max follow-ups reached.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why advancing: satisfied, max_followups, time_constraint, candidate_request"
                },
                "satisfaction_score": {
                    "type": "number",
                    "description": "How satisfied with the answer (0.0 to 1.0)"
                },
                "brief_feedback": {
                    "type": "string",
                    "description": "Brief positive acknowledgment for the candidate"
                }
            },
            "required": ["reason", "satisfaction_score"]
        }
    },
    {
        "name": "end_interview",
        "description": "Conclude the interview session. Use when all questions are complete or interview should end early.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why ending: completed, time_up, candidate_request, technical_issue"
                },
                "closing_message": {
                    "type": "string",
                    "description": "Professional closing message for the candidate"
                }
            },
            "required": ["reason"]
        }
    },
]


# =============================================================================
# Tool Implementations
# =============================================================================

@dataclass
class ToolResult:
    """Result from executing a tool."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


def execute_respond_to_candidate(
    response_type: str,
    candidate_said: str,
    tone: str,
    next_topic: Optional[str] = None,
    **kwargs
) -> ToolResult:
    """Generate a natural conversational response to the candidate."""
    system_prompt = """You are a warm, professional technical interviewer having a natural conversation.
Generate a response that sounds human, not robotic. Keep it concise (1-2 sentences max).
Return JSON only."""

    tone_guidance = {
        "encouraging": "Be warm and positive, acknowledge their effort",
        "neutral": "Be professional and matter-of-fact",
        "probing": "Show curiosity, lean in with interest"
    }

    type_guidance = {
        "acknowledge": "Briefly acknowledge what they said before asking a follow-up",
        "transition": "Smoothly move to the next topic, referencing what they said",
        "feedback": "Give brief, constructive feedback on their answer",
        "clarify": "Gently ask them to elaborate or explain what they meant"
    }

    user_prompt = f"""Generate a natural interviewer response.

What candidate said: "{candidate_said}"
Response type: {response_type} - {type_guidance.get(response_type, '')}
Tone: {tone} - {tone_guidance.get(tone, '')}
{f'Next topic to introduce: {next_topic}' if next_topic else ''}

Return JSON:
{{
    "response": "Your natural response here (1-2 sentences, conversational)",
    "introduces_topic": true/false
}}

Examples of good responses:
- "Interesting approach! I'd love to hear more about how you handled the error cases."
- "That's a solid foundation. Let's shift gears and talk about system design."
- "I see what you mean. Could you walk me through a specific example?"
- "Great, thanks for sharing that. Now, thinking about scalability..."
"""

    try:
        response = call_llm(system_prompt, user_prompt)
        response = _clean_json_response(response)
        data = json.loads(response)
        return ToolResult(success=True, data=data)
    except Exception as e:
        # Fallback to simple responses
        fallback_responses = {
            "acknowledge": "I hear you.",
            "transition": "Let's move on to the next topic.",
            "feedback": "Thanks for that response.",
            "clarify": "Could you tell me more about that?"
        }
        return ToolResult(
            success=True,
            data={"response": fallback_responses.get(response_type, "I see.")},
            error=str(e)
        )




def execute_analyze_answer(
    answer_text: str,
    question_context: str,
    role_level: str = "mid",
    **kwargs
) -> ToolResult:
    """Analyze the candidate's answer."""
    system_prompt = """You are an expert technical interviewer evaluating answers.
Analyze the answer objectively and return JSON only."""

    user_prompt = f"""Analyze this interview answer.

Question: {question_context}
Answer: {answer_text}
Expected Level: {role_level}

Return JSON:
{{
    "score": 0.0-1.0,
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"],
    "needs_followup": true/false,
    "followup_type": "clarify" | "probe_deeper" | "challenge" | null,
    "summary": "one line assessment"
}}"""

    try:
        response = call_llm(system_prompt, user_prompt)
        response = _clean_json_response(response)
        data = json.loads(response)
        return ToolResult(success=True, data=data)
    except Exception as e:
        return ToolResult(
            success=False,
            data={"score": 0.5, "strengths": [], "gaps": [], "needs_followup": False},
            error=str(e)
        )


def execute_evaluate_code(
    code: str,
    question: str,
    reference_solution: Optional[str] = None,
    **kwargs
) -> ToolResult:
    """Evaluate the candidate's code."""
    system_prompt = """You are a senior engineer reviewing code.
Evaluate objectively and return JSON only."""

    ref_context = f"\nReference Solution:\n{reference_solution}" if reference_solution else ""

    user_prompt = f"""Evaluate this code submission.

Question: {question}
{ref_context}

Candidate Code:
```
{code}
```

Return JSON:
{{
    "score": 0.0-1.0,
    "correctness": 0.0-1.0,
    "efficiency": 0.0-1.0,
    "style": 0.0-1.0,
    "strengths": ["strength1"],
    "issues": ["issue1"],
    "would_compile": true/false,
    "needs_followup": true/false,
    "followup_type": "clarify" | "probe_deeper" | "challenge" | null
}}"""

    try:
        response = call_llm(system_prompt, user_prompt, prefer="groq")
        response = _clean_json_response(response)
        data = json.loads(response)
        return ToolResult(success=True, data=data)
    except Exception as e:
        return ToolResult(
            success=False,
            data={"score": 0.5, "correctness": 0.5, "issues": [], "needs_followup": False},
            error=str(e)
        )


def execute_ask_followup(
    followup_type: str,
    focus_area: str,
    context: str,
    previous_followups: Optional[List[str]] = None,
    **kwargs
) -> ToolResult:
    """Generate a follow-up question."""
    system_prompt = """You are a skilled interviewer. Generate ONE concise follow-up question.
Return JSON only."""

    prev_context = ""
    if previous_followups:
        prev_context = "\nPrevious follow-ups (avoid repetition):\n" + "\n".join(
            f"- {f}" for f in previous_followups[-2:]
        )

    user_prompt = f"""Generate a follow-up question.

Context: {context}
Follow-up Type: {followup_type}
Focus Area: {focus_area}
{prev_context}

Return JSON:
{{
    "followup_question": "Your question here?",
    "rationale": "Why asking this"
}}"""

    try:
        response = call_llm(system_prompt, user_prompt)
        response = _clean_json_response(response)
        data = json.loads(response)

        # Apply guardrails to the generated question
        question = data.get("followup_question", "")
        filtered = filter_question(question)
        if filtered:
            data["followup_question"] = filtered
            return ToolResult(success=True, data=data)
        else:
            return ToolResult(
                success=False,
                data={"followup_question": None},
                error="Question failed guardrails"
            )
    except Exception as e:
        return ToolResult(
            success=False,
            data={"followup_question": None},
            error=str(e)
        )


def execute_give_hint(
    hint_level: str,
    topic_area: str,
    question_context: str,
    **kwargs
) -> ToolResult:
    """Generate a hint for the candidate."""
    system_prompt = """You are a supportive interviewer providing hints.
Keep hints appropriate to the level requested. Return JSON only."""

    level_guidance = {
        "gentle": "Give a vague nudge in the right direction without revealing the answer",
        "moderate": "Point toward the general approach or concept needed",
        "direct": "Provide a specific pointer but still require the candidate to work it out"
    }

    user_prompt = f"""Generate a hint for a stuck candidate.

Question Context: {question_context}
Topic Area: {topic_area}
Hint Level: {hint_level}
Guidance: {level_guidance.get(hint_level, level_guidance['moderate'])}

Return JSON:
{{
    "hint": "Your hint here",
    "follow_on": "Optional encouraging phrase"
}}"""

    try:
        response = call_llm(system_prompt, user_prompt)
        response = _clean_json_response(response)
        data = json.loads(response)
        return ToolResult(success=True, data=data)
    except Exception as e:
        return ToolResult(
            success=False,
            data={"hint": "Think about the core concept here."},
            error=str(e)
        )


def execute_advance_to_next(
    reason: str,
    satisfaction_score: float,
    brief_feedback: Optional[str] = None,
    **kwargs
) -> ToolResult:
    """Signal to advance to the next question."""
    return ToolResult(
        success=True,
        data={
            "action": "advance",
            "reason": reason,
            "satisfaction_score": satisfaction_score,
            "feedback": brief_feedback or "Good, let's move on."
        }
    )


def execute_end_interview(
    reason: str,
    closing_message: Optional[str] = None,
    **kwargs
) -> ToolResult:
    """Signal to end the interview."""
    default_closing = "Thank you for your time today. We'll be in touch soon."
    return ToolResult(
        success=True,
        data={
            "action": "end",
            "reason": reason,
            "closing_message": closing_message or default_closing
        }
    )


# =============================================================================
# Tool Registry
# =============================================================================

TOOL_IMPLEMENTATIONS = {
    "respond_to_candidate": execute_respond_to_candidate,
    "analyze_answer": execute_analyze_answer,
    "evaluate_code": execute_evaluate_code,
    "ask_followup": execute_ask_followup,
    "give_hint": execute_give_hint,
    "advance_to_next": execute_advance_to_next,
    "end_interview": execute_end_interview,
}


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas for the agent."""
    return TOOL_SCHEMAS


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> ToolResult:
    """Execute a tool by name with given arguments."""
    if tool_name not in TOOL_IMPLEMENTATIONS:
        return ToolResult(
            success=False,
            data={},
            error=f"Unknown tool: {tool_name}"
        )

    try:
        impl = TOOL_IMPLEMENTATIONS[tool_name]
        return impl(**tool_args)
    except Exception as e:
        return ToolResult(
            success=False,
            data={},
            error=f"Tool execution error: {str(e)}"
        )


# =============================================================================
# Helpers
# =============================================================================

def _clean_json_response(response: str) -> str:
    """Clean LLM response to extract JSON."""
    response = response.strip()
    if "```json" in response:
        response = response.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in response:
        response = response.split("```", 1)[1].split("```", 1)[0].strip()
    return response
