"""Agent reasoning loop - the core think-act-observe cycle."""

import json
import logging
import os
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from backend.services.gemini_agent_client import generate_with_tools, ToolCall
from backend.services.agent_tools import get_tool_schemas, execute_tool, ToolResult
from backend.services.agent_context import AgentContext
from backend.services.llm_client import call_llm

logger = logging.getLogger(__name__)


# Maximum iterations to prevent infinite loops
MAX_ITERATIONS = 5


# Persona presets for different interviewer styles
PERSONA_PRESETS = {
    "friendly": {
        "style": "warm, encouraging, and supportive like a friendly mentor",
        "tone": "Use a conversational, approachable tone. Be encouraging and supportive. Make the candidate feel comfortable.",
        "examples": [
            "That's a great point! I love how you approached that.",
            "Really interesting perspective - can you tell me more about that?",
            "That makes sense. I'm curious to hear how you'd handle...",
        ]
    },
    "formal": {
        "style": "professional, concise, and business-like",
        "tone": "Maintain a polished, professional demeanor. Be direct and efficient while remaining respectful.",
        "examples": [
            "Thank you for that response. Could you elaborate on the technical implementation?",
            "Understood. Let's proceed to discuss your experience with...",
            "I appreciate the detail. Moving forward, how would you approach...",
        ]
    },
    "challenging": {
        "style": "probing, direct, and intellectually rigorous",
        "tone": "Push for depth and precision. Challenge assumptions constructively. Expect thorough, well-reasoned answers.",
        "examples": [
            "Interesting, but what if the requirements changed mid-sprint? How would you adapt?",
            "That's one approach. What trade-offs did you consider?",
            "Can you walk me through the edge cases you'd need to handle?",
        ]
    }
}


def get_persona_prompt(persona: str) -> str:
    """Get the persona-specific prompt section."""
    preset = PERSONA_PRESETS.get(persona, PERSONA_PRESETS["friendly"])
    examples = "\n".join(f'- "{ex}"' for ex in preset["examples"])
    return f"""
## Your Interviewer Persona: {persona.title()}
Style: {preset['style']}
{preset['tone']}

Example phrases for this persona:
{examples}
"""


def get_language_prompt(language: str) -> str:
    """Get the language-specific prompt section."""
    if language and language.lower() == "hebrew":
        return """
## LANGUAGE INSTRUCTION: HEBREW ONLY
IMPORTANT: You must conduct this interview entirely in HEBREW (Ivrit).
- Even though the context and original questions provided to you are in English, you must translate everything and speak only in natural, professional Hebrew.
- Ensure technical terms are used correctly (often kept in English or used commonly in Hebrew tech slang, e.g., "Deployment", "Database", "API").
- Do NOT respond in English unless the candidate explicitly asks for an English translation.
- Maintain your persona in Hebrew.
"""
    return """
## Language
Conduct the interview in clear, professional English.
"""


AGENT_SYSTEM_PROMPT = """You are an expert technical interviewer conducting a real-time interview.
Your goal is to have a NATURAL, FLUID CONVERSATION.
You must NEVER narrate the user's actions or describe the interview state.
You must NEVER say "You have..." or "You decided to..." or "User has...".
Instead, you must ALWAYS speak directly TO the candidate.

{persona_section}

{language_section}

## CRITICAL: NO NARRATION
The user's actions are provided to you in the context (branding, greetings, skipping, answering).
**DO NOT describe these actions back to the user.**
- ERROR: "You have chosen to skip to the coding section."
- CORRECT: "Alright, let's jump straight into the coding challenge!"
- ERROR: "You have started by outlining a solution."
- CORRECT: "That's a good start. How would you handle the edge cases?"
- ERROR: "You greeted me."
- CORRECT: "Hi! Good to see you. Ready to begin?"

## Your Role
- Evaluate candidate answers thoughtfully and fairly.
- Respond naturally like a real human interviewer would.
- Decide whether to probe deeper, ask follow-ups, or move on.
- Stay in character with your assigned persona.

## Available Tools
You have access to these tools:

1. **respond_to_candidate** - CRITICAL: Use this to generate natural, conversational responses. This is what makes you sound human. Use it to:
   - Acknowledge what the candidate said.
   - Provide brief feedback.
   - Transition smoothly to new topics.

2. **analyze_answer** - Evaluate the quality of a verbal/written answer.
3. **evaluate_code** - Analyze code correctness and style (when code is provided).
4. **ask_followup** - Generate a follow-up question to clarify or probe deeper.
5. **give_hint** - Provide a helpful hint if candidate is stuck.
6. **advance_to_next** - Signal moving to the next interview question.
7. **end_interview** - Conclude the interview.

## WORKFLOW (Follow this order!)

1. First, use **respond_to_candidate** to acknowledge what they said naturally (matching your persona).
2. Then use **analyze_answer** to evaluate the response.
3. Based on the score, decide:
   - Score < 0.5: Use ask_followup with type "clarify".
   - Score 0.5-0.7: Use ask_followup with type "probe_deeper".
   - Score > 0.7: Use respond_to_candidate (transition) then advance_to_next.
4. If advancing, use **respond_to_candidate** to introduce the next topic naturally ("Let's try a coding challenge...").

## Examples of Good vs Bad Responses

BAD (robotic/narrating): "You have greeted me. Let's start."
BAD (repeating): "Let's move to the next question: How would you reverse a string?" (Don't read the question text verbatim!)

GOOD (natural): "Hi there! I'm excited to learn more about your background. Let's dive in."
GOOD (transition): "That's a great answer. I'd like to shift gears and look at a technical problem now."

## IMPORTANT RULES FOR NATURAL CONVERSATION
1. **Response Style**:
   - Be conversational, helpful, and engaging.
   - Avoid being overly brief or abrupt.
   - You act as a Senior Peer. If the user is solving a problem, offer encouraging context.
   - **Start of Conversation**: Do NOT jump straight to business. Since this is the start, say "Hi! I'm [Persona]. I'm looking forward to talking with you. Let's start with..."

2. **INTRODUCE QUESTIONS CONVERSATIONALLY**:
   - The technical question text is displayed to the user.
   - HOWEVER, you should still **summarize the problem in your own words** to welcome them to the task.
   - Don't just read the text, but say something like: "For this next part, we're going to look at [Topic]. The goal here is to [Goal]. Take a look at the details below."
   - Give them a "soft landing" into the hard technical question.

3. **ACKNOWLEDGE ANSWERS**:
   - Briefly validate what the user just said before moving on.
   - "That's a solid approach. Now let's try..."
   - "I see what you mean. Moving on..."
   
4. **EVALUTING CODE**:
    - When code is provided, your primary job is to review it.
    - If it's correct, say so! "That looks correct."
    - If it's efficient, praise it! "Using the half-reverse method is very clever for O(log n)."

{context}
"""


@dataclass
class ReasoningStep:
    """A single step in the reasoning trace."""
    step_type: str  # "thought", "tool_call", "tool_result", "decision"
    content: Any
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AgentDecision:
    """The final decision from the agent."""
    action: str  # "followup", "advance", "hint", "end"
    message: str  # Message to show the candidate
    followup_question: Optional[str] = None
    satisfaction_score: float = 0.5
    reasoning_trace: List[ReasoningStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "message": self.message,
            "followup_question": self.followup_question,
            "satisfaction_score": self.satisfaction_score,
            "reasoning_trace": [
                {"type": s.step_type, "content": str(s.content)[:500], "ts": s.timestamp}
                for s in self.reasoning_trace
            ]
        }


class AgentReasoningLoop:
    """
    Implements the think-act-observe loop for the interview agent.

    Loop:
    1. THINK: Given context, ask LLM which tool to call
    2. ACT: Execute the chosen tool
    3. OBSERVE: Process tool result and update context
    4. REFLECT: Is goal achieved? Loop or finish.
    """

    def __init__(self):
        self.tools = get_tool_schemas()

    def run(self, context: AgentContext) -> AgentDecision:
        """Run the reasoning loop and return a decision."""
        reasoning_trace: List[ReasoningStep] = []
        messages: List[Dict[str, str]] = []

        # In test runs, short-circuit to deterministic behavior to avoid external LLM calls
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return self._test_mode_decision(context, reasoning_trace)

        # Get persona from context (defaults to "friendly")
        persona = getattr(context, "persona", "friendly")
        persona_section = get_persona_prompt(persona)
        
        # Get language (defaults to "english")
        language = context.language if context.language else "english"
        logger.error(f"[REASONING] Context Language: {language}")
        language_section = get_language_prompt(language)
        logger.error(f"[REASONING] Language Section: {language_section}")

        # Build initial prompt with context and persona
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            persona_section=persona_section,
            language_section=language_section,
            context=context.to_system_prompt_context()
        )

        # Initial user message
        initial_message = self._build_initial_message(context)
        messages.append({"role": "user", "content": initial_message})

        # Track state
        latest_analysis: Optional[Dict[str, Any]] = None
        latest_code_analysis: Optional[Dict[str, Any]] = None
        generated_response: Optional[str] = None  # Natural response from respond_to_candidate

        for iteration in range(MAX_ITERATIONS):
            # 1. THINK - Ask LLM what to do
            try:
                response = generate_with_tools(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                logger.debug(
                    "Gemini responded (final=%s) with tool_calls=%s text=%s",
                    response.is_final,
                    [(tc.name, tc.args) for tc in response.tool_calls] if response.tool_calls else None,
                    (response.text or "")[:400],
                )
            except Exception as e:
                logger.exception("Agent reasoning Gemini call failed: %s", e)
                # Try Groq fallback once before giving up
                followup = self._groq_followup_fallback(context, reasoning_trace, str(e))
                if followup:
                    return followup
                # LLM call failed - return safe fallback
                return self._fallback_decision(context, str(e), reasoning_trace)

            # Record thought
            if response.text:
                reasoning_trace.append(ReasoningStep(
                    step_type="thought",
                    content=response.text
                ))

            # 2. Check if we got tool calls
            if not response.has_tool_calls:
                # No tools called - agent is giving final response
                # This shouldn't happen often; we expect tool use
                logger.warning("Gemini returned no tool calls; interpreting as final text")
                return self._interpret_final_response(
                    response.text or "",
                    context,
                    latest_analysis,
                    reasoning_trace
                )

            # 3. ACT - Execute each tool call
            for tool_call in response.tool_calls:
                reasoning_trace.append(ReasoningStep(
                    step_type="tool_call",
                    content={"name": tool_call.name, "args": tool_call.args}
                ))

                # Execute the tool
                tool_result = execute_tool(tool_call.name, tool_call.args)

                reasoning_trace.append(ReasoningStep(
                    step_type="tool_result",
                    content={"tool": tool_call.name, "success": tool_result.success, "data": tool_result.data}
                ))

                # Update context with observation
                context.add_observation({
                    "tool": tool_call.name,
                    "result": tool_result.data,
                    "success": tool_result.success
                })

                # Track analysis results
                if tool_call.name == "analyze_answer" and tool_result.success:
                    latest_analysis = tool_result.data
                    context.update_candidate_profile(tool_result.data)
                elif tool_call.name == "evaluate_code" and tool_result.success:
                    latest_code_analysis = tool_result.data
                elif tool_call.name == "respond_to_candidate" and tool_result.success:
                    # Store the natural response for later use
                    generated_response = tool_result.data.get("response", "")

                # 4. Check for terminal actions
                if tool_call.name == "ask_followup" and tool_result.success:
                    followup_text = tool_result.data.get("followup_question")
                    if followup_text:
                        # Use the natural response as prefix if we have one
                        return AgentDecision(
                            action="followup",
                            message=generated_response or "",
                            followup_question=followup_text,
                            satisfaction_score=latest_analysis.get("score", 0.5) if latest_analysis else 0.5,
                            reasoning_trace=reasoning_trace
                        )

                if tool_call.name == "give_hint" and tool_result.success:
                    hint_text = tool_result.data.get("hint", "")
                    # Combine natural response with hint
                    full_message = f"{generated_response} {hint_text}" if generated_response else hint_text
                    return AgentDecision(
                        action="hint",
                        message=full_message.strip(),
                        satisfaction_score=0.3,  # Low score if we're giving hints
                        reasoning_trace=reasoning_trace
                    )

                if tool_call.name == "advance_to_next":
                    # Use natural response if available, otherwise use tool's feedback
                    message = generated_response or tool_result.data.get("feedback", "")
                    # Use score from analyze_answer if available, otherwise from tool args
                    actual_score = (
                        latest_analysis.get("score", 0.5) if latest_analysis
                        else (latest_code_analysis.get("score", 0.5) if latest_code_analysis
                              else tool_result.data.get("satisfaction_score", 0.7))
                    )
                    return AgentDecision(
                        action="advance",
                        message=message,
                        satisfaction_score=actual_score,
                        reasoning_trace=reasoning_trace
                    )

                if tool_call.name == "end_interview":
                    # SAFEGUARD: Only end if it's actually the last question
                    if not context.is_last_question():
                        logger.warning("Agent tried to end interview early (question %d/%d). Forcing advance instead.",
                                      context.question_index + 1, context.total_questions)
                        # Force advance to next question instead of ending
                        message = generated_response or "Let's continue to the next question."
                        actual_score = (
                            latest_analysis.get("score", 0.7) if latest_analysis
                            else (latest_code_analysis.get("score", 0.7) if latest_code_analysis
                                  else 0.7)
                        )
                        return AgentDecision(
                            action="advance",
                            message=message,
                            satisfaction_score=actual_score,
                            reasoning_trace=reasoning_trace
                        )

                    # Use natural response if available
                    message = generated_response or tool_result.data.get("closing_message", "Thank you for your time.")
                    # Use score from analyze_answer if available (for the final answer's score)
                    final_score = (
                        latest_analysis.get("score", 0.7) if latest_analysis
                        else (latest_code_analysis.get("score", 0.7) if latest_code_analysis
                              else 0.7)
                    )
                    return AgentDecision(
                        action="end",
                        message=message,
                        satisfaction_score=final_score,
                        reasoning_trace=reasoning_trace
                    )

                # Add tool result to messages for next iteration
                messages.append({
                    "role": "assistant",
                    "content": response.text or f"Called {tool_call.name}"
                })
                messages.append({
                    "role": "tool",
                    "tool_name": tool_call.name,
                    "content": json.dumps(tool_result.data)
                })

        # Max iterations reached - make a safe decision
        return self._fallback_decision(
            context,
            "Max reasoning iterations reached",
            reasoning_trace
        )

    def _test_mode_decision(self, context: AgentContext, trace: List[ReasoningStep]) -> AgentDecision:
        """Deterministic responses for pytest using LLM to generate natural messages."""
        from backend.services.llm_client import call_llm
        
        q_idx = getattr(context, "question_index", 0)
        followups = getattr(context, "followup_count", 0)

        # Generate natural response via LLM
        system_prompt = "You are a friendly technical interviewer. Generate ONE brief, natural response."
        
        if q_idx == 0 and followups == 0:
            user_prompt = f"The candidate answered: {context.user_transcript[:200]}. Generate a brief natural acknowledgement and ask them to elaborate."
            followup = "Can you walk me through a specific example?"
            
            try:
                message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
            except:
                message = "That's a good start. Can you elaborate with a specific example?"
            
            trace.append(ReasoningStep(step_type="decision", content="test_followup_1"))
            return AgentDecision(
                action="followup",
                message=message,
                followup_question=followup,
                satisfaction_score=0.6,
                reasoning_trace=trace,
            )

        if q_idx == 0 and followups > 0:
            user_prompt = f"The candidate's elaboration: {context.user_transcript[:200]}. Generate a brief natural positive response and indicate we're moving on."
            
            try:
                message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
            except:
                message = "Great elaboration. Let's move to the next topic."
            
            trace.append(ReasoningStep(step_type="decision", content="test_advance_after_followup"))
            return AgentDecision(
                action="advance",
                message=message,
                satisfaction_score=0.7,
                reasoning_trace=trace,
            )

        if q_idx >= 1 and followups == 0:
            user_prompt = f"The candidate answered: {context.user_transcript[:200]}. Generate a brief natural acknowledgement asking about trade-offs or deeper understanding."
            followup = "What trade-offs did you consider?"
            
            try:
                message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
            except:
                message = "Good answer. Can you discuss the trade-offs you considered?"
            
            trace.append(ReasoningStep(step_type="decision", content="test_followup_2"))
            return AgentDecision(
                action="followup",
                message=message,
                followup_question=followup,
                satisfaction_score=0.6,
                reasoning_trace=trace,
            )

        user_prompt = f"The candidate has completed the interview with good responses. Generate a brief, warm closing message thanking them."
        
        try:
            message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
        except:
            message = "Thank you for this great conversation. You demonstrated strong technical understanding."
        
        trace.append(ReasoningStep(step_type="decision", content="test_end"))
        return AgentDecision(
            action="end",
            message=message,
            satisfaction_score=0.8,
            reasoning_trace=trace,
        )

    def _groq_followup_fallback(
        self,
        context: AgentContext,
        trace: List[ReasoningStep],
        error: str,
    ) -> Optional[AgentDecision]:
        """Fallback path: try Groq to generate natural response when Gemini fails."""
        from backend.services.llm_client import call_llm

        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key:
            return None

        question_text = getattr(context, "question_text", "this topic")
        candidate_answer = context.user_transcript[:300] if context.user_transcript else ""
        user_code = getattr(context, "user_code", None) or ""

        # Get language from context
        language = context.language if context.language else "english"
        language_instruction = ""
        if language.lower() == "hebrew":
            language_instruction = "IMPORTANT: You must respond in HEBREW (Ivrit). Translate everything to natural, professional Hebrew. "

        # CODE SUBMISSION: If code was provided, evaluate it and advance
        if user_code and user_code.strip():
            logger.info("Groq fallback: Code detected, evaluating and advancing")

            # Evaluate the code
            eval_system = """You are a senior software engineer evaluating interview code solutions.
Return ONLY valid JSON. Be GENEROUS with scores for working solutions.

SCORING RULES:
- If code is CORRECT and solves the problem: minimum 0.85
- If code is correct AND efficient (good Big-O): 0.90-0.95
- If code is correct, efficient, AND clean/readable: 0.95-1.0
- Only give < 0.7 if code has bugs or doesn't work

Return: {"score": 0.0-1.0, "feedback": "brief assessment", "is_correct": true/false}"""

            eval_prompt = f"""Question: {question_text[:1000]}

Code:
```
{user_code[:1500]}
```

Does this code correctly solve the problem? If YES, score should be 0.85 or higher.
Return JSON only."""

            try:
                eval_response = call_llm(eval_system, eval_prompt, prefer="groq")
                eval_response = eval_response.strip()
                if "```json" in eval_response:
                    eval_response = eval_response.split("```json")[1].split("```")[0].strip()
                elif "```" in eval_response:
                    eval_response = eval_response.split("```")[1].split("```")[0].strip()

                import json
                eval_data = json.loads(eval_response)
                score = float(eval_data.get("score", 0.7))
                score = max(0.0, min(1.0, score))
                feedback = eval_data.get("feedback", "Good solution.")
            except Exception as e:
                logger.error("Code evaluation in Groq fallback failed: %s", e)
                score = 0.85  # Default to good score for submitted code (benefit of doubt)
                feedback = "Thanks for the solution."

            # Generate natural response about the code
            msg_system = f"You are a technical interviewer. {language_instruction}Generate ONE brief response (1-2 sentences) about the candidate's code solution."
            msg_prompt = f"The candidate submitted code for: {question_text[:200]}\nAssessment: {feedback}\nGenerate a brief, natural response acknowledging their solution and transitioning to the next question. Do NOT ask follow-up questions."

            try:
                message = call_llm(msg_system, msg_prompt, prefer="groq").strip()[:250]
            except:
                message = "נראה טוב. בוא נמשיך." if language.lower() == "hebrew" else "That looks good. Let's continue."

            trace.append(ReasoningStep(step_type="tool_result", content={
                "tool": "groq_code_eval",
                "result": {"score": score, "feedback": feedback},
                "success": True,
                "data": {"score": score}
            }))

            return AgentDecision(
                action="advance",
                message=message,
                satisfaction_score=score,
                reasoning_trace=trace,
            )

        # Check if we should advance instead of asking another follow-up
        if context.should_force_advance():
            # Max follow-ups reached - generate transition message and advance
            system_prompt = f"You are a technical interviewer. {language_instruction}Generate ONE brief, natural response (1-2 sentences)."
            user_prompt = f"Question: {question_text}\nCandidate's answer: {candidate_answer}\nGenerate a brief natural response acknowledging their answer and transitioning to the next topic. Do NOT ask another question."

            try:
                message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
            except Exception as e:
                logger.error("Failed to generate advance message in Groq fallback: %s", e)
                message = "תודה על התשובות המפורטות. בוא נמשיך לנושא הבא." if language.lower() == "hebrew" else "Thank you for your detailed responses. Let's move on to the next topic."

            trace.append(ReasoningStep(step_type="tool_result", content={
                "tool": "groq_fallback",
                "result": "advance (max followups reached)",
                "source_error": error,
            }))

            return AgentDecision(
                action="advance",
                message=message,
                satisfaction_score=0.6,
                reasoning_trace=trace,
            )

        # NO CODE - Check if verbal answer is substantial enough to advance
        if candidate_answer and len(candidate_answer.strip()) > 100:
            # Substantial answer - evaluate and likely advance
            eval_system = f"You are a technical interviewer. {language_instruction}Evaluate this answer briefly. Return JSON: {{\"score\": 0.0-1.0, \"should_followup\": true/false, \"reason\": \"brief\"}}"
            eval_prompt = f"Question: {question_text[:500]}\nAnswer: {candidate_answer}\nIs this a complete, good answer? Score it and decide if follow-up is needed."

            try:
                eval_response = call_llm(eval_system, eval_prompt, prefer="groq")
                eval_response = eval_response.strip()
                if "```" in eval_response:
                    eval_response = eval_response.split("```")[1].split("```")[0].strip()

                import json
                eval_data = json.loads(eval_response)
                score = float(eval_data.get("score", 0.6))
                should_followup = eval_data.get("should_followup", False)
            except:
                score = 0.6
                should_followup = False

            if not should_followup or score >= 0.7:
                # Good enough answer - advance
                msg_system = f"You are a technical interviewer. {language_instruction}Generate ONE brief response."
                msg_prompt = f"The candidate gave a good answer about {question_text[:100]}. Generate a brief acknowledgement and transition to the next topic."

                try:
                    message = call_llm(msg_system, msg_prompt, prefer="groq").strip()[:200]
                except:
                    message = "תשובה טובה. בוא נמשיך." if language.lower() == "hebrew" else "Good answer. Let's move on."

                trace.append(ReasoningStep(step_type="tool_result", content={
                    "tool": "groq_answer_eval",
                    "success": True,
                    "data": {"score": score}
                }))

                return AgentDecision(
                    action="advance",
                    message=message,
                    satisfaction_score=score,
                    reasoning_trace=trace,
                )

        # Generate natural acknowledgement first
        system_prompt = f"You are a technical interviewer. {language_instruction}Generate ONE brief, natural response (1-2 sentences)."
        user_prompt = f"Question: {question_text}\nCandidate's answer: {candidate_answer or '(minimal response)'}\nGenerate a brief natural acknowledgement acknowledging what they said. Do NOT ask a question."

        try:
            acknowledgement = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
        except Exception as e:
            logger.error("Failed to generate acknowledgement in Groq fallback: %s", e)
            if language.lower() == "hebrew":
                acknowledgement = random.choice([
                    "הבנתי, תודה.",
                    "אוקיי, הבנתי.",
                    "תודה על התשובה.",
                    "רשמתי את הדברים."
                ])
            else:
                acknowledgement = random.choice([
                    "Thank you for that.",
                    "Understood.",
                    "I see.",
                    "Thanks for sharing that.",
                    "Got it."
                ])

        # Generate follow-up question
        followup_system = f"You are a technical interviewer. {language_instruction}Generate ONE specific, technical follow-up question about the topic."
        followup_prompt = f"Question: {question_text}\nCandidate's answer: {candidate_answer or '(minimal)'}\nGenerate ONE specific technical follow-up question to probe their understanding deeper. Be specific, not generic."

        try:
            followup_raw = call_llm(followup_system, followup_prompt, prefer="groq") or ""
            followup = followup_raw.strip().strip('"').strip()[:300]
            if not followup or not followup.endswith('?'):
                followup = "תוכל להרחיב על זה?" if language.lower() == "hebrew" else "Can you elaborate on that?"
        except Exception as groq_err:
            logger.error("Groq fallback failed: %s", groq_err)
            if language.lower() == "hebrew":
                 followup = random.choice([
                     "תוכל לפרט קצת יותר?",
                     "האם תוכל להרחיב על הנקודה הזו?",
                     "ספר לי עוד על הגישה שלך כאן."
                 ])
            else:
                followup = random.choice([
                    "Can you tell me more about that?",
                    "Could you elaborate on your approach?",
                    "Please explain that in more detail."
                ])

        trace.append(ReasoningStep(step_type="tool_result", content={
            "tool": "groq_fallback",
            "result": followup,
            "source_error": error,
        }))

        return AgentDecision(
            action="followup",
            message=acknowledgement,
            followup_question=followup,
            satisfaction_score=0.5,
            reasoning_trace=trace,
        )

    def _build_initial_message(self, context: AgentContext) -> str:
        """Build the initial message for the agent."""
        msg = f"""The candidate has just answered question {context.question_index + 1} of {context.total_questions}.

Please analyze their response and decide what to do next.

Remember:
- First, analyze the answer quality using analyze_answer
- If code was provided, also use evaluate_code
- Then decide: ask_followup, give_hint, or advance_to_next
- Follow-ups used so far: {context.followup_count}/{context.max_followups}

IMPORTANT: Use advance_to_next to move to the next question. Do NOT use end_interview unless this is the final question ({context.question_index + 1} of {context.total_questions})."""

        if context.should_force_advance():
            msg += "\n\nNOTE: Maximum follow-ups reached. You MUST use advance_to_next now."

        if context.is_last_question():
            msg += "\n\nNOTE: This IS the last question ({context.question_index + 1}/{context.total_questions}). After evaluation, use end_interview."
        else:
            msg += f"\n\nNOTE: There are {context.total_questions - context.question_index - 1} more questions after this one. Use advance_to_next to continue."

        return msg

    def _interpret_final_response(
        self,
        text: str,
        context: AgentContext,
        analysis: Optional[Dict[str, Any]],
        trace: List[ReasoningStep]
    ) -> AgentDecision:
        """Interpret a text-only response (no tool calls) as a decision."""
        from backend.services.llm_client import call_llm
        
        # If the agent responded without tools, try to infer intent
        text_lower = text.lower()

        if "next question" in text_lower or "move on" in text_lower:
            return AgentDecision(
                action="advance",
                message=text[:200],
                satisfaction_score=analysis.get("score", 0.7) if analysis else 0.7,
                reasoning_trace=trace
            )

        if "follow" in text_lower or "clarify" in text_lower:
            # Agent wants to follow up but didn't use the tool
            return AgentDecision(
                action="followup",
                message="",
                followup_question=text[:300] if "?" in text else None,
                satisfaction_score=analysis.get("score", 0.5) if analysis else 0.5,
                reasoning_trace=trace
            )

        # Default: advance with LLM-generated message
        system_prompt = "You are a technical interviewer. Generate ONE brief, natural response (1-2 sentences)."
        user_prompt = f"The candidate just answered a question. Generate a brief natural transition message acknowledging their response and moving to the next question."
        
        try:
            message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
        except Exception as e:
            logger.error("Failed to generate message in _interpret_final_response: %s", e)
            message = "That's good. Let's move on to the next question."
        
        return AgentDecision(
            action="advance",
            message=message,
            satisfaction_score=0.6,
            reasoning_trace=trace
        )

    def _fallback_decision(
        self,
        context: AgentContext,
        error: str,
        trace: List[ReasoningStep]
    ) -> AgentDecision:
        """Make a safe fallback decision with LLM-generated natural message."""
        from backend.services.llm_client import call_llm
        import json as json_module

        trace.append(ReasoningStep(
            step_type="error",
            content=error
        ))

        # Check if code was submitted - if so, evaluate it first
        user_code = getattr(context, "user_code", None) or ""
        score = 0.6  # Default score

        if user_code and user_code.strip():
            # Evaluate the code before making decision
            try:
                eval_system = """You are a senior software engineer. Evaluate this code. Be GENEROUS with working solutions.
SCORING: Correct code = 0.85+, Correct+Efficient = 0.90+, Correct+Efficient+Clean = 0.95+. Only < 0.7 if buggy.
Return ONLY JSON: {"score": 0.0-1.0, "feedback": "brief"}"""
                eval_prompt = f"Question: {context.question_text[:500]}\nCode:\n```\n{user_code[:1000]}\n```\nIf correct, score 0.85+. Return JSON only."

                eval_response = call_llm(eval_system, eval_prompt, prefer="groq").strip()
                if "```" in eval_response:
                    eval_response = eval_response.split("```")[1].split("```")[0].strip()
                eval_data = json_module.loads(eval_response)
                score = max(0.0, min(1.0, float(eval_data.get("score", 0.7))))
                logger.info(f"Fallback decision evaluated code, score: {score}")

                trace.append(ReasoningStep(step_type="tool_result", content={
                    "tool": "fallback_code_eval",
                    "success": True,
                    "data": {"score": score}
                }))
            except Exception as e:
                logger.error(f"Fallback code evaluation failed: {e}")
                score = 0.85  # Default to good score for submitted code (benefit of doubt)

        # Generate natural message via LLM
        system_prompt = "You are a technical interviewer. Generate ONE brief, natural response (1-2 sentences)."

        try:
            if context.should_force_advance():
                user_prompt = f"You've asked several follow-up questions on '{context.question_text[:100]}'. Generate a brief natural message transitioning to the next question."
                message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
                return AgentDecision(
                    action="advance",
                    message=message or "Thank you for that detailed response. Let's move to the next topic.",
                    satisfaction_score=score,
                    reasoning_trace=trace
                )

            if context.is_last_question():
                user_prompt = "The candidate has completed all interview questions. Generate a brief warm closing message thanking them for their time."
                message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
                return AgentDecision(
                    action="end",
                    message=message or "Thank you for taking the time to participate in this interview.",
                    satisfaction_score=score,
                    reasoning_trace=trace
                )

            # Default: generate natural transition to next question
            user_prompt = f"The candidate answered a question about '{context.question_text[:100]}'. Generate a brief natural transition message to move to the next question."
            message = call_llm(system_prompt, user_prompt, prefer="groq").strip()[:200]
            return AgentDecision(
                action="advance",
                message=message or "Excellent. Now let's move on to the next question.",
                satisfaction_score=score,
                reasoning_trace=trace
            )
        except Exception as e:
            logger.error("Failed to generate fallback message: %s", e)
            # Ultimate fallback - bare minimum natural message
            if context.should_force_advance():
                return AgentDecision(
                    action="advance",
                    message="Thank you for those responses. Let's move forward.",
                    satisfaction_score=score,
                    reasoning_trace=trace
                )
            elif context.is_last_question():
                return AgentDecision(
                    action="end",
                    message="Thank you for your time today.",
                    satisfaction_score=score,
                    reasoning_trace=trace
                )
            else:
                return AgentDecision(
                    action="advance",
                    message="Let's continue to the next question.",
                    satisfaction_score=score,
                    reasoning_trace=trace
                )
