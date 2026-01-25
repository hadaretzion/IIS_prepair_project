"""Interview agent orchestrator with true agentic flow.

Provides AgenticInterviewAgent - a true agent with reasoning loop and tool use.
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlmodel import Session, select

from backend.models import InterviewSession, InterviewTurn, QuestionBank
from backend.schemas import InterviewNextRequest
from backend.services.agent_context import AgentContext, build_context_from_request
from backend.services.agent_reasoning import AgentReasoningLoop, AgentDecision

logger = logging.getLogger(__name__)


def _load_state(interview_session: InterviewSession) -> Dict[str, Any]:
    state = json.loads(interview_session.conversation_state_json or "{}")
    return {
        "current_question_id": state.get("current_question_id"),
        "followup_count": state.get("followup_count", 0),
        "question_index": state.get("question_index", 0),
        "initial_answer_score": state.get("initial_answer_score", 0),
        "previous_followups": state.get("previous_followups", []),
    }


def _save_state(interview_session: InterviewSession, state: Dict[str, Any], session: Session) -> None:
    interview_session.conversation_state_json = json.dumps(state)
    session.add(interview_session)
    session.commit()


def _get_last_main_turn(session_id: str, session: Session) -> Optional[InterviewTurn]:
    return session.exec(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .where(InterviewTurn.is_followup == False)
        .order_by(InterviewTurn.turn_index.desc())
    ).first()


class AgenticInterviewAgent:
    """
    True agentic interview orchestrator with reasoning loop.

    Uses:
    - Gemini function calling for tool use
    - Think-act-observe loop for autonomous decision making
    - Agent context for memory and state
    """

    def __init__(self):
        self.reasoning_loop = AgentReasoningLoop()


    def _refine_and_translate(self, text: str, type: str, language: str) -> str:
        """Refine and optionally translate the question using LLM."""
        from backend.services.llm_client import call_llm
        
        # If Hebrew, we want strict Hebrew translation + refinement
        if language and language.lower() == "hebrew":
            prompt = f"""Task: Translate and Refine Interview Question for a Professional Job Interview.
Target Language: Hebrew (Ivrit).
Instructions:
1. Translate the following interview question to professional, natural Hebrew.
2. Frame the question as a professional interviewer would ask it in a real job interview.
3. Keep the tone professional, direct, and respectful - like a senior hiring manager.
4. For technical questions, you may add brief context (e.g., "In our team, we often deal with...").
5. For behavioral questions, ask directly without elaborate storytelling.
6. Do NOT use casual phrases like "let's grab coffee" or "imagine you're chatting with a friend".
7. Output ONLY the final Hebrew question text.

Original Question: "{text}"
Question Type: {type}

Hebrew Question:"""
            try:
                result = call_llm("You are a professional job interviewer conducting a formal interview.", prompt, prefer="groq")
                if result and result.strip():
                    return result.strip()
            except Exception as e:
                logger.error(f"Refinement/Translation failed: {e}")
                return text # Fallback to original

        # English Refinement
        prompt = f"""Task: Refine Interview Question for a Professional Job Interview.
Instructions:
1. Rewrite the question as a professional interviewer would ask it in a real job interview.
2. Keep the tone professional, direct, and respectful - like a senior hiring manager or tech lead.
3. For technical questions, you may add brief real-world context (e.g., "In production systems, we often need to...").
4. For behavioral questions, ask directly and professionally without elaborate storytelling or casual scenarios.
5. Do NOT use casual phrases like "grab a coffee", "imagine you're chatting", or "let's pretend".
6. The question should feel like it's coming from an experienced interviewer, not a friend.
7. Output ONLY the refined question text.

Original Question: "{text}"
Question Type: {type}

Refined Question:"""
        try:
            result = call_llm("You are a professional job interviewer conducting a formal interview.", prompt, prefer="groq")
            if result and result.strip():
                return result.strip()
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
        
        return text

    def process_turn(
        self,
        request: InterviewNextRequest,
        interview_session: InterviewSession,
        plan_items: List[Dict[str, Any]],
        role_profile: Dict[str, Any],
        session: Session,
    ) -> Dict[str, Any]:
        """Process a turn using the agentic reasoning loop."""
        state = _load_state(interview_session)
        followup_count = state["followup_count"]
        question_index = state["question_index"]
        previous_followups = state["previous_followups"]

        # Check if interview is complete
        if followup_count == 0 and question_index >= len(plan_items):
            interview_session.ended_at = datetime.utcnow()
            session.add(interview_session)
            session.commit()
            return {
                "interviewer_message": "Thank you! The interview is complete.",
                "followup_question": None,
                "next_question": None,
                "is_done": True,
                "progress": {"turn_index": question_index, "total": len(plan_items)},
            }

        # Get current question
        plan_item = plan_items[question_index] if question_index < len(plan_items) else {}
        question_id = state.get("current_question_id") if followup_count > 0 else plan_item.get("selected_question_id")

        question = session.get(QuestionBank, question_id)
        if not question:
            return self._error_response(question_index, len(plan_items))

        # --- REFINEMENT CHECK ---
        # Check if we have a refined version of this question in state
        refined_key = f"refined_q_{question_index}"
        
        # SAFETY: Detach 'question' from session before modifying text
        # This prevents the refined/translated text from overwriting the original in the database
        session.expunge(question)

        if refined_key in state:
            # Use the pre-calculated refined text for the Agent's context
            question.question_text = state[refined_key]
        else:
            # If not in state (e.g. first run or legacy), try to refine now
            # Get language directly from session
            lang = interview_session.language if interview_session.language else "english"
            
            # Refine/Translate
            refined_text = self._refine_and_translate(question.question_text, plan_item.get("type", "open"), lang)
            
            # Updates
            state[refined_key] = refined_text
            question.question_text = refined_text
            
            # We need to save this state update
            _save_state(interview_session, state, session)
        # ------------------------

        # Build agent context
        # Get persona from interview session (defaults to "friendly")
        persona = getattr(interview_session, "persona", "friendly")
        # Get language (defaults to "english")
        language = interview_session.language if interview_session.language else "english"
        logger.error(f"[AGENT] Session Language: {language}")
        
        context = build_context_from_request(
            session_id=request.session_id,
            question=question,
            request=request,
            plan_items=plan_items,
            role_profile=role_profile,
            state=state,
            persona=persona,
            language=language
        )

        # Run the reasoning loop
        try:
            decision = self.reasoning_loop.run(context)
        except Exception as e:
            logger.error(f"Agent reasoning failed: {e}")
            # Fallback to advancing on error
            decision = AgentDecision(
                action="advance",
                message="Let's continue with the next question.",
                satisfaction_score=0.5,
                reasoning_trace=[]
            )

        # Record the turn
        turn = self._create_turn(
            request=request,
            question=question,
            question_index=question_index,
            followup_count=followup_count,
            decision=decision,
            session=session,
        )
        session.add(turn)
        session.commit()

        # Process the decision
        return self._process_decision(
            decision=decision,
            question=question,
            question_id=question_id,
            question_index=question_index,
            followup_count=followup_count,
            previous_followups=previous_followups,
            plan_items=plan_items,
            interview_session=interview_session,
            state=state,
            session=session,
            language=language,
        )

    def _process_decision(
        self,
        decision: AgentDecision,
        question: QuestionBank,
        question_id: str,
        question_index: int,
        followup_count: int,
        previous_followups: List[str],
        plan_items: List[Dict[str, Any]],
        interview_session: InterviewSession,
        state: Dict[str, Any],
        session: Session,
        language: str = "english",
    ) -> Dict[str, Any]:
        """Process the agent's decision and return API response."""

        if decision.action == "followup" and decision.followup_question:
            # Agent wants to ask a follow-up
            state["current_question_id"] = question_id
            state["followup_count"] = followup_count + 1
            state["initial_answer_score"] = decision.satisfaction_score
            state["previous_followups"] = previous_followups + [decision.followup_question]
            _save_state(interview_session, state, session)

            # Use agent's natural response - if empty, just use the followup directly
            if decision.message:
                message = decision.message
            else:
                # Agent didn't generate natural response - use followup question directly
                message = decision.followup_question

            return {
                "interviewer_message": message,
                "followup_question": {"text": decision.followup_question},
                "next_question": None,
                "is_done": False,
                "progress": {"turn_index": question_index + 1, "total": len(plan_items)},
                "agent_decision": decision.action,
                "agent_confidence": decision.satisfaction_score,
            }

        if decision.action == "hint":
            # Agent is giving a hint (stay on same question)
            # Use agent's message directly - it should contain natural response + hint
            return {
                "interviewer_message": decision.message or "Let me give you a hint.",
                "followup_question": None,
                "next_question": None,
                "is_done": False,
                "progress": {"turn_index": question_index + 1, "total": len(plan_items)},
                "agent_decision": decision.action,
            }

        if decision.action == "end":
            # SAFEGUARD: Double-check we're actually at the last question
            if question_index < len(plan_items) - 1:
                logger.warning(
                    "Agent returned 'end' but we're at question %d/%d. Forcing advance instead.",
                    question_index + 1, len(plan_items)
                )
                # Override to advance instead
                decision = AgentDecision(
                    action="advance",
                    message=decision.message or "Let's continue to the next question.",
                    satisfaction_score=decision.satisfaction_score,
                    reasoning_trace=decision.reasoning_trace
                )
                # Fall through to advance handling below
            else:
                # Actually the last question - end the interview
                logger.info("Ending interview at question %d/%d", question_index + 1, len(plan_items))
                interview_session.ended_at = datetime.utcnow()
                session.add(interview_session)
                session.commit()
                return {
                    "interviewer_message": decision.message or "Thank you for your time today.",
                    "followup_question": None,
                    "next_question": None,
                    "is_done": True,
                    "progress": {"turn_index": question_index + 1, "total": len(plan_items)},
                    "agent_decision": decision.action,
                }

        # Default: advance to next question
        state["question_index"] = question_index + 1
        state["followup_count"] = 0
        state["previous_followups"] = []
        _save_state(interview_session, state, session)

        next_question_data = self._get_next_question_data(
            question_index + 1, plan_items, session, language, interview_session, state
        )

        interview_session.question_start_time = datetime.utcnow()
        session.add(interview_session)
        session.commit()

        # Build the message: use agent's natural response
        if decision.message:
            # Agent generated a natural transition
            message = decision.message
        else:
            # Agent didn't generate transition - provide the next question directly
            if next_question_data:
                message = "בוא נמשיך לשאלה הבאה." if language.lower() == "hebrew" else "Let's move to the next question."
            else:
                message = "מצוין! בוא נמשיך." if language.lower() == "hebrew" else "Great! Let's continue."
                
        return {
            "interviewer_message": message,
            "followup_question": None,
            "next_question": next_question_data,
            "is_done": question_index + 1 >= len(plan_items),
            "progress": {"turn_index": question_index + 1, "total": len(plan_items)},
            "agent_decision": decision.action,
            "agent_confidence": decision.satisfaction_score,
        }

    def _create_turn(
        self,
        request: InterviewNextRequest,
        question: QuestionBank,
        question_index: int,
        followup_count: int,
        decision: AgentDecision,
        session: Session,
    ) -> InterviewTurn:
        """Create an InterviewTurn record."""
        topics = json.loads(question.topics_json or "[]")

        # Build detailed score_json with rubric from reasoning trace
        score_data = {"overall": decision.satisfaction_score}
        found_evaluation = False

        # Extract detailed analysis from reasoning trace
        for step in decision.reasoning_trace:
            if step.step_type == "tool_result" and isinstance(step.content, dict):
                tool_name = step.content.get("tool", "")
                tool_data = step.content.get("data", {})

                if tool_name == "analyze_answer" and step.content.get("success"):
                    found_evaluation = True
                    # Extract rubric details from answer analysis
                    if "score" in tool_data:
                        score_data["overall"] = tool_data["score"]
                    if "strengths" in tool_data:
                        score_data["strengths"] = tool_data["strengths"]
                    if "gaps" in tool_data:
                        score_data["gaps"] = tool_data["gaps"]
                    if "summary" in tool_data:
                        score_data["notes"] = [tool_data["summary"]]

                elif tool_name == "evaluate_code" and step.content.get("success"):
                    found_evaluation = True
                    # Extract rubric from code evaluation
                    rubric = {}
                    if "correctness" in tool_data:
                        rubric["correctness"] = tool_data["correctness"]
                    if "efficiency" in tool_data:
                        rubric["efficiency"] = tool_data["efficiency"]
                    if "style" in tool_data:
                        rubric["style"] = tool_data["style"]
                    if rubric:
                        score_data["rubric"] = rubric
                    if "score" in tool_data:
                        score_data["overall"] = tool_data["score"]
                    if "issues" in tool_data:
                        score_data["notes"] = tool_data.get("notes", []) + tool_data["issues"]

        # FALLBACK: If no evaluation was found, directly evaluate the answer/code
        if not found_evaluation and (request.user_transcript or request.user_code):
            logger.info("No evaluation found in reasoning trace, running fallback evaluation")
            fallback_score = self._fallback_evaluate(
                question.question_text,
                request.user_transcript,
                request.user_code
            )
            if fallback_score:
                score_data.update(fallback_score)

        turn = InterviewTurn(
            id=str(uuid.uuid4()),
            session_id=request.session_id,
            turn_index=len(session.exec(
                select(InterviewTurn).where(InterviewTurn.session_id == request.session_id)
            ).all()),
            question_id=question.id,
            question_snapshot=question.question_text,
            user_transcript=request.user_transcript,
            user_code=request.user_code,
            score_json=json.dumps(score_data),
            topics_json=json.dumps(topics),
            parent_turn_id=None,
            question_number=question_index,
            is_followup=followup_count > 0,
            time_spent_seconds=getattr(request, "elapsed_seconds", 0) or 0,
            agent_analysis_json=json.dumps(decision.to_dict()),
        )

        if followup_count > 0:
            parent_turn = _get_last_main_turn(request.session_id, session)
            if parent_turn:
                turn.parent_turn_id = parent_turn.id

        return turn

    def _fallback_evaluate(
        self,
        question_text: str,
        user_transcript: Optional[str],
        user_code: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback evaluation when agent tools don't produce a score.
        Directly calls LLM to evaluate the answer/code.
        """
        from backend.services.llm_client import call_llm

        # Determine if this is a code question
        has_code = bool(user_code and user_code.strip())
        content_to_evaluate = user_code if has_code else (user_transcript or "")

        if not content_to_evaluate.strip():
            return None

        try:
            if has_code:
                # Evaluate code
                system_prompt = """You are a senior software engineer evaluating interview code solutions.
Be GENEROUS with scores for working solutions. Most interview candidates with correct code should pass.
Return ONLY valid JSON."""

                user_prompt = f"""Evaluate this code solution.

Question/Problem:
{question_text[:1500]}

Candidate's Code:
```
{user_code[:2000]}
```

Return JSON:
{{
    "overall": 0.0-1.0 (overall quality score),
    "rubric": {{
        "correctness": 0.0-1.0 (does it solve the problem correctly?),
        "efficiency": 0.0-1.0 (is it efficient? O(n) vs O(n^2) etc),
        "style": 0.0-1.0 (clean, readable, well-structured?)
    }},
    "strengths": ["strength1", "strength2"],
    "notes": ["note about the solution"]
}}

IMPORTANT SCORING RULES - Be generous:
- If code is CORRECT and solves the problem: overall should be 0.85 or higher
- If code is correct AND has good time complexity: overall should be 0.90-0.95
- If code is correct, efficient, AND well-written: overall should be 0.95-1.0
- Only give below 0.7 if the code has actual bugs or doesn't solve the problem
- This is an interview - reward working solutions!"""

            else:
                # Evaluate verbal answer
                system_prompt = """You are a technical interviewer evaluating candidate answers.
Analyze the response objectively for completeness, accuracy, and clarity.
Return ONLY valid JSON."""

                user_prompt = f"""Evaluate this interview answer.

Question:
{question_text[:1500]}

Candidate's Answer:
{user_transcript[:2000]}

Return JSON:
{{
    "overall": 0.0-1.0 (overall quality score),
    "strengths": ["strength1", "strength2"],
    "gaps": ["gap1", "gap2"],
    "notes": ["brief assessment"]
}}

Scoring guide:
- 0.9-1.0: Excellent - comprehensive, accurate, well-articulated
- 0.7-0.89: Good - solid answer with minor gaps
- 0.5-0.69: Acceptable - partial answer or lacks depth
- 0.3-0.49: Poor - significant gaps or inaccuracies
- 0.0-0.29: Very poor - doesn't address the question"""

            response = call_llm(system_prompt, user_prompt, prefer="groq")

            # Parse JSON response
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            result = json.loads(response)

            # Ensure overall is a valid float
            # Default to 0.85 for code (benefit of doubt), 0.6 for verbal answers
            default_score = 0.85 if has_code else 0.6
            overall = float(result.get("overall", default_score))
            overall = max(0.0, min(1.0, overall))
            result["overall"] = overall

            logger.info(f"Fallback evaluation produced score: {overall}")
            return result

        except Exception as e:
            logger.error(f"Fallback evaluation failed: {e}")
            # Return a default score instead of None for code submissions
            if has_code:
                return {"overall": 0.85, "notes": ["Code submitted - evaluation pending"]}
            return None

    def _get_next_question_data(
        self,
        next_index: int,
        plan_items: List[Dict[str, Any]],
        session: Session,
        language: str = "english",
        interview_session: Optional[InterviewSession] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the next question data if available."""
        if next_index >= len(plan_items):
            return None

        next_item = plan_items[next_index]
        next_question_id = next_item.get("selected_question_id")
        next_question = session.get(QuestionBank, next_question_id)

        if next_question:
            question_text = next_question.question_text
            
            # Helper to save state if we refine content
            refined_key = f"refined_q_{next_index}"
            
            # Check if we already refined it (if state provided)
            if state and refined_key in state:
                question_text = state[refined_key]
            else:
                # Refine/Translate now
                question_text = self._refine_and_translate(
                    next_question.question_text, 
                    next_item.get("type", "open"), 
                    language
                )
                
                # Save to state if possible so we don't re-run or lose consistency
                if state is not None and interview_session:
                    state[refined_key] = question_text
                    # We utilize the helper _save_state but we need to ensure we don't conflict 
                    # with other saves. Since this is usually called from process_decision which just saved,
                    # we do another save.
                    try:
                        _save_state(interview_session, state, session)
                    except Exception as e:
                        logger.error(f"Failed to save refined question state: {e}")

            return {
                "question_id": next_question.id,
                "text": question_text,
                "type": next_item.get("type", "open"),
                "topics": json.loads(next_question.topics_json or "[]"),
            }
        return None

    def _error_response(self, question_index: int, total: int) -> Dict[str, Any]:
        """Return an error response."""
        return {
            "interviewer_message": "Sorry, I hit an error loading the question.",
            "followup_question": None,
            "next_question": None,
            "is_done": True,
            "progress": {"turn_index": question_index, "total": total},
        }


# =============================================================================
# Legacy Implementation (State Machine)
# =============================================================================

class InterviewAgent:
    """
    Interview agent using true agentic flow with reasoning loop and tool use.
    """

    def __init__(self):
        self._agentic = AgenticInterviewAgent()

    def process_turn(
        self,
        request: InterviewNextRequest,
        interview_session: InterviewSession,
        plan_items: List[Dict[str, Any]],
        role_profile: Dict[str, Any],
        session: Session,
    ) -> Dict[str, Any]:
        """Process a turn using agentic flow."""
        logger.info("Using agentic interview flow")
        return self._agentic.process_turn(
            request, interview_session, plan_items, role_profile, session
        )


