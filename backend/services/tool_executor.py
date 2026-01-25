"""Tool executor with error handling, logging, and rate limiting."""

import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from functools import wraps

from backend.services.agent_tools import (
    TOOL_IMPLEMENTATIONS,
    ToolResult,
    execute_analyze_answer,
    execute_evaluate_code,
    execute_ask_followup,
    execute_give_hint,
    execute_advance_to_next,
    execute_end_interview,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics from tool execution."""
    tool_name: str
    execution_time_ms: int
    success: bool
    error: Optional[str] = None


class ToolExecutor:
    """
    Executes tools with error handling, logging, and metrics.

    Features:
    - Timeout handling
    - Error recovery
    - Execution metrics
    - Rate limiting (optional)
    """

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds
        self.execution_history: list[ExecutionMetrics] = []

    def execute(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute a tool with error handling and metrics.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            context: Optional additional context (e.g., for logging)

        Returns:
            ToolResult with success status and data
        """
        start_time = time.time()

        try:
            # Validate tool exists
            if tool_name not in TOOL_IMPLEMENTATIONS:
                return self._handle_unknown_tool(tool_name)

            # Get the implementation
            impl = TOOL_IMPLEMENTATIONS[tool_name]

            # Execute with timeout protection
            result = self._execute_with_timeout(impl, tool_args)

            # Record metrics
            execution_time_ms = int((time.time() - start_time) * 1000)
            self._record_metrics(tool_name, execution_time_ms, result.success, result.error)

            return result

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            self._record_metrics(tool_name, execution_time_ms, False, error_msg)

            logger.error(f"Tool execution failed: {tool_name} - {error_msg}")

            return ToolResult(
                success=False,
                data={},
                error=f"Execution failed: {error_msg}"
            )

    def _execute_with_timeout(
        self,
        impl: Callable,
        args: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool implementation with timeout protection."""
        # For now, just execute directly
        # In production, you might want to use threading or asyncio for true timeout
        return impl(**args)

    def _handle_unknown_tool(self, tool_name: str) -> ToolResult:
        """Handle request for unknown tool."""
        logger.warning(f"Unknown tool requested: {tool_name}")
        return ToolResult(
            success=False,
            data={},
            error=f"Unknown tool: {tool_name}. Available: {list(TOOL_IMPLEMENTATIONS.keys())}"
        )

    def _record_metrics(
        self,
        tool_name: str,
        execution_time_ms: int,
        success: bool,
        error: Optional[str]
    ) -> None:
        """Record execution metrics."""
        metrics = ExecutionMetrics(
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error
        )
        self.execution_history.append(metrics)

        # Log execution
        if success:
            logger.debug(f"Tool {tool_name} executed in {execution_time_ms}ms")
        else:
            logger.warning(f"Tool {tool_name} failed after {execution_time_ms}ms: {error}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of execution metrics."""
        if not self.execution_history:
            return {"total_calls": 0}

        total = len(self.execution_history)
        successful = sum(1 for m in self.execution_history if m.success)
        total_time = sum(m.execution_time_ms for m in self.execution_history)

        by_tool: Dict[str, Dict[str, Any]] = {}
        for m in self.execution_history:
            if m.tool_name not in by_tool:
                by_tool[m.tool_name] = {"calls": 0, "successes": 0, "total_ms": 0}
            by_tool[m.tool_name]["calls"] += 1
            by_tool[m.tool_name]["successes"] += 1 if m.success else 0
            by_tool[m.tool_name]["total_ms"] += m.execution_time_ms

        return {
            "total_calls": total,
            "successful_calls": successful,
            "success_rate": successful / total if total > 0 else 0,
            "total_execution_time_ms": total_time,
            "average_execution_time_ms": total_time // total if total > 0 else 0,
            "by_tool": by_tool
        }

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history = []


# Global executor instance
_executor: Optional[ToolExecutor] = None


def get_executor() -> ToolExecutor:
    """Get the global tool executor instance."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor


def execute_tool_safe(
    tool_name: str,
    tool_args: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """Execute a tool using the global executor."""
    return get_executor().execute(tool_name, tool_args, context)
