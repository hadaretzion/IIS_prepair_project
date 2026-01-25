"""Gemini AI client with function calling support for agentic workflows."""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Import existing client setup
from backend.services.gemini_client import client, API_KEY, is_rate_limit_error

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call from the model."""
    name: str
    args: Dict[str, Any]


@dataclass
class AgentResponse:
    """Response from the agent, either a tool call or final text."""
    text: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    is_final: bool = False

    @property
    def has_tool_calls(self) -> bool:
        return self.tool_calls is not None and len(self.tool_calls) > 0


def _convert_to_gemini_tools(tools: List[Dict[str, Any]]) -> List[types.FunctionDeclaration]:
    """Convert tool definitions to Gemini FunctionDeclaration format."""
    declarations = []
    for tool in tools:
        # Convert JSON Schema to Gemini Schema format
        params = tool.get("parameters", {})
        properties = params.get("properties", {})
        required = params.get("required", [])

        # Build Gemini-compatible schema
        gemini_properties = {}
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "string")
            gemini_prop = {"type": prop_type.upper()}

            if "description" in prop_def:
                gemini_prop["description"] = prop_def["description"]
            if "enum" in prop_def:
                gemini_prop["enum"] = prop_def["enum"]
            if prop_type == "array" and "items" in prop_def:
                gemini_prop["items"] = {"type": prop_def["items"].get("type", "string").upper()}

            gemini_properties[prop_name] = gemini_prop

        declaration = types.FunctionDeclaration(
            name=tool["name"],
            description=tool.get("description", ""),
            parameters=types.Schema(
                type="OBJECT",
                properties=gemini_properties,
                required=required,
            ) if gemini_properties else None,
        )
        declarations.append(declaration)

    return declarations


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True,
)
def generate_with_tools(
    system_prompt: str,
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]],
    tool_choice: str = "auto",
) -> AgentResponse:
    """
    Generate a response with tool calling capability.

    Args:
        system_prompt: System instructions for the agent
        messages: Conversation history [{"role": "user"|"assistant"|"tool", "content": "..."}]
        tools: List of tool definitions in JSON Schema format
        tool_choice: "auto" (model decides), "any" (must call a tool), "none" (no tools)

    Returns:
        AgentResponse with either text or tool_calls
    """
    if not API_KEY or not client:
        logger.error("Gemini API not configured (API_KEY present: %s)", bool(API_KEY))
        raise ValueError("Gemini API not configured.")

    # Convert tools to Gemini format
    function_declarations = _convert_to_gemini_tools(tools)

    # Build contents from messages
    contents = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=content)]
            ))
        elif role == "assistant":
            contents.append(types.Content(
                role="model",
                parts=[types.Part(text=content)]
            ))
        elif role == "tool":
            # Tool result - include as function response
            tool_name = msg.get("tool_name", "unknown")
            contents.append(types.Content(
                role="user",
                parts=[types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={"result": content}
                    )
                )]
            ))

    # Configure tool usage
    tool_config = None
    if tool_choice == "any":
        tool_config = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        )
    elif tool_choice == "none":
        tool_config = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="NONE")
        )
    # "auto" is default, no config needed

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(function_declarations=function_declarations)] if function_declarations else None,
                tool_config=tool_config,
                temperature=0.3,
                max_output_tokens=4096,
            )
        )

        # Parse response
        if not response.candidates:
            logger.warning("Gemini returned no candidates for tool call request")
            return AgentResponse(text="No response generated.", is_final=True)

        candidate = response.candidates[0]

        # Check for tool calls
        tool_calls = []
        text_parts = []

        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    name=fc.name,
                    args=dict(fc.args) if fc.args else {}
                ))
            elif hasattr(part, 'text') and part.text:
                text_parts.append(part.text)

        if tool_calls:
            logger.debug("Gemini tool calls: %s | text: %s", [(t.name, t.args) for t in tool_calls], "\n".join(text_parts) if text_parts else None)
            return AgentResponse(
                text="\n".join(text_parts) if text_parts else None,
                tool_calls=tool_calls,
                is_final=False
            )
        else:
            logger.debug("Gemini returned text-only response (no tool calls): %s", "\n".join(text_parts) if text_parts else "")
            return AgentResponse(
                text="\n".join(text_parts) if text_parts else "",
                is_final=True
            )

    except Exception as e:
        error_msg = str(e)
        logger.exception("Gemini tool call failed: %s", error_msg)
        raise ValueError(f"Gemini API error: {error_msg}")


def generate_with_tools_streaming(
    system_prompt: str,
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]],
):
    """
    Streaming version of generate_with_tools.
    Yields partial responses as they come in.
    """
    # For now, just use the non-streaming version
    # Can be enhanced later for real streaming support
    yield generate_with_tools(system_prompt, messages, tools)
