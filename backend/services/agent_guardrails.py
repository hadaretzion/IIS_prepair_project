"""Guardrails for the interview agent.

This module provides safety mechanisms for the agentic interview flow:
1. Question content filtering (no discriminatory questions)
2. Tool call validation
3. Runaway loop detection
4. Response content filtering
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# Question Content Guardrails
# =============================================================================

UNSAFE_PATTERNS = [
    r"\b(age|birthday|birthdate|dob)\b",
    r"\b(race|ethnicity|ethnic|skin color)\b",
    r"\b(religion|religious|church|mosque|synagogue)\b",
    r"\b(sexual orientation|sexuality|pregnan|pregnancy|marital|marriage)\b",
    r"\b(gender identity|gender|transgender|nonbinary)\b",
    r"\b(nationality|citizenship|immigration|visa)\b",
    r"\b(disability|disabled|medical condition|health condition)\b",
    r"\b(political|politics|party affiliation)\b",
    r"\b(criminal record|arrest|conviction)\b",
]

SAFE_EXCEPTIONS = [
    "race condition",
    "data race",
    "gender equality",  # Technical discussions about inclusivity
]


def is_question_allowed(question: str) -> bool:
    """Return False if question likely violates boundary rules."""
    if not question:
        return True

    lower = question.lower()
    if any(exc in lower for exc in SAFE_EXCEPTIONS):
        return True

    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return False

    return True


def filter_question(question: str) -> Optional[str]:
    """Return question if allowed, else None."""
    return question if is_question_allowed(question) else None


# =============================================================================
# Tool Call Validation
# =============================================================================

VALID_TOOLS = {
    "respond_to_candidate",
    "analyze_answer",
    "evaluate_code",
    "ask_followup",
    "give_hint",
    "advance_to_next",
    "end_interview",
}

# Tools that should only be called once per turn
SINGLE_USE_TOOLS = {
    "ask_followup",
    "give_hint",
    "advance_to_next",
    "end_interview",
}

# Maximum times a tool can be called in one reasoning loop
MAX_TOOL_CALLS_PER_TYPE = {
    "respond_to_candidate": 2,  # May generate transition + acknowledgement
    "analyze_answer": 2,  # Might re-analyze after code eval
    "evaluate_code": 2,
    "ask_followup": 1,
    "give_hint": 1,
    "advance_to_next": 1,
    "end_interview": 1,
}


@dataclass
class ToolCallValidation:
    """Result of tool call validation."""
    is_valid: bool
    error: Optional[str] = None


def validate_tool_call(
    tool_name: str,
    tool_args: Dict[str, Any],
    previous_calls: List[str],
) -> ToolCallValidation:
    """
    Validate a tool call before execution.

    Checks:
    - Tool exists
    - Not exceeding max calls
    - Required args present
    """
    # Check tool exists
    if tool_name not in VALID_TOOLS:
        return ToolCallValidation(
            is_valid=False,
            error=f"Unknown tool: {tool_name}"
        )

    # Check call count
    call_count = previous_calls.count(tool_name)
    max_calls = MAX_TOOL_CALLS_PER_TYPE.get(tool_name, 3)

    if call_count >= max_calls:
        return ToolCallValidation(
            is_valid=False,
            error=f"Tool {tool_name} already called {call_count} times (max: {max_calls})"
        )

    # Validate tool-specific args
    if tool_name == "ask_followup":
        if not tool_args.get("followup_type"):
            return ToolCallValidation(
                is_valid=False,
                error="ask_followup requires followup_type"
            )
        if tool_args.get("followup_type") not in ["clarify", "probe_deeper", "challenge"]:
            return ToolCallValidation(
                is_valid=False,
                error=f"Invalid followup_type: {tool_args.get('followup_type')}"
            )

    if tool_name == "give_hint":
        if tool_args.get("hint_level") and tool_args["hint_level"] not in ["gentle", "moderate", "direct"]:
            return ToolCallValidation(
                is_valid=False,
                error=f"Invalid hint_level: {tool_args.get('hint_level')}"
            )

    return ToolCallValidation(is_valid=True)


# =============================================================================
# Runaway Loop Detection
# =============================================================================

MAX_ITERATIONS = 5
MAX_TOTAL_TOOL_CALLS = 10


@dataclass
class LoopStatus:
    """Status of the reasoning loop."""
    should_stop: bool
    reason: Optional[str] = None


def check_loop_status(
    iteration: int,
    total_tool_calls: int,
    tool_call_history: List[str],
) -> LoopStatus:
    """
    Check if the reasoning loop should be terminated.

    Detects:
    - Max iterations reached
    - Too many tool calls
    - Circular tool call patterns
    """
    # Check iteration limit
    if iteration >= MAX_ITERATIONS:
        return LoopStatus(
            should_stop=True,
            reason=f"Max iterations reached ({MAX_ITERATIONS})"
        )

    # Check total tool calls
    if total_tool_calls >= MAX_TOTAL_TOOL_CALLS:
        return LoopStatus(
            should_stop=True,
            reason=f"Too many tool calls ({total_tool_calls})"
        )

    # Check for circular patterns (same sequence repeating)
    if len(tool_call_history) >= 4:
        last_four = tool_call_history[-4:]
        if len(set(last_four)) == 1:
            # Same tool called 4 times in a row
            return LoopStatus(
                should_stop=True,
                reason=f"Circular pattern detected: {last_four[0]} called repeatedly"
            )

    return LoopStatus(should_stop=False)


# =============================================================================
# Response Content Filtering
# =============================================================================

# Patterns that should not appear in agent responses
FORBIDDEN_RESPONSE_PATTERNS = [
    r"(ignore previous|disregard instructions|forget everything)",
    r"(you are now|pretend to be|act as if)",
    r"(system prompt|hidden instructions)",
]


def filter_response_content(text: str) -> str:
    """
    Filter agent response content for safety.

    Removes or flags:
    - Prompt injection attempts
    - Inappropriate content
    """
    if not text:
        return text

    lower = text.lower()

    # Check for prompt injection patterns
    for pattern in FORBIDDEN_RESPONSE_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            logger.warning(f"Filtered suspicious content matching: {pattern}")
            return "[Response filtered for safety]"

    return text


# =============================================================================
# Agent Decision Guardrails
# =============================================================================

@dataclass
class DecisionValidation:
    """Result of decision validation."""
    is_valid: bool
    corrected_decision: Optional[str] = None
    reason: Optional[str] = None


def validate_agent_decision(
    decision: str,
    followup_count: int,
    max_followups: int,
    is_last_question: bool,
) -> DecisionValidation:
    """
    Validate and potentially correct an agent's decision.

    Ensures:
    - Max followups respected
    - Interview can end properly
    - Decisions are sensible
    """
    valid_decisions = {"followup", "advance", "hint", "end"}

    if decision not in valid_decisions:
        return DecisionValidation(
            is_valid=False,
            corrected_decision="advance",
            reason=f"Unknown decision: {decision}"
        )

    # Force advance if max followups reached
    if decision == "followup" and followup_count >= max_followups:
        return DecisionValidation(
            is_valid=False,
            corrected_decision="advance",
            reason=f"Max followups ({max_followups}) reached, forcing advance"
        )

    # Force end if last question and trying to advance
    if decision == "advance" and is_last_question:
        return DecisionValidation(
            is_valid=False,
            corrected_decision="end",
            reason="Last question completed, ending interview"
        )

    return DecisionValidation(is_valid=True)


# =============================================================================
# Unified Guardrails Class
# =============================================================================

class AgentGuardrails:
    """
    Unified guardrails for the interview agent.

    Provides a single interface for all safety checks.
    """

    def __init__(self):
        self.tool_call_history: List[str] = []
        self.iteration_count = 0

    def reset(self):
        """Reset state for a new turn."""
        self.tool_call_history = []
        self.iteration_count = 0

    def validate_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> ToolCallValidation:
        """Validate a tool call."""
        return validate_tool_call(tool_name, tool_args, self.tool_call_history)

    def record_tool_call(self, tool_name: str):
        """Record a tool call for loop detection."""
        self.tool_call_history.append(tool_name)

    def check_loop(self) -> LoopStatus:
        """Check if the loop should stop."""
        self.iteration_count += 1
        return check_loop_status(
            self.iteration_count,
            len(self.tool_call_history),
            self.tool_call_history
        )

    def filter_question(self, question: str) -> Optional[str]:
        """Filter a generated question."""
        return filter_question(question)

    def filter_response(self, text: str) -> str:
        """Filter response content."""
        return filter_response_content(text)

    def validate_decision(
        self,
        decision: str,
        followup_count: int,
        max_followups: int = 3,
        is_last_question: bool = False,
    ) -> DecisionValidation:
        """Validate an agent decision."""
        return validate_agent_decision(
            decision, followup_count, max_followups, is_last_question
        )
