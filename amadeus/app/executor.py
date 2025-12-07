"""
Amadeus Action Executor

Executor actions - last stage of the pipeline.
Executes approved ActionPlan through appropriate adapters.

Security:
- Pre-execution validation for each action
- Execution timeouts
- Detailed logging of results
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amadeus.core.entities import (
    Action,
    ActionPlan,
    ExecutionResult,
    ExecutionStatus,
    RiskLevel,
)
from amadeus.core.policy import PreExecutionValidator

logger = logging.getLogger(__name__)


@dataclass
class ExecutorConfig:
    """Executor configuration."""

    # Timeouts
    action_timeout_seconds: float = 30.0
    total_timeout_seconds: float = 120.0

    # Security
    validate_before_execution: bool = True
    stop_on_first_error: bool = True

    # Logging
    log_outputs: bool = True
    max_output_length: int = 10000


class ActionExecutor:
    """
    Executor actions.

    Executes ActionPlan through appropriate OS adapters.
    Each action undergoes pre-execution validation.

    Example:
    ```python
    from amadeus.adapters.os import get_os_adapter
    
    adapter = get_os_adapter()
    executor = ActionExecutor(adapter)
    
    results = executor.execute_plan(plan)
    for result in results:
        if result.is_success:
            print(f"✓ {result.action.description}")
        else:
            print(f"✗ {result.action.description}: {result.error}")
    ```
    """

    def __init__(
        self,
        os_adapter: Any,
        config: Optional[ExecutorConfig] = None,
    ) -> None:
        self.os_adapter = os_adapter
        self.config = config or ExecutorConfig()
        self.validator = PreExecutionValidator()
        
        # Mapping tool_name -> adapter method group
        self._tool_handlers: Dict[str, Any] = {
            "filesystem": self.os_adapter,
            "process": self.os_adapter,
            "browser": self.os_adapter,
            "system": self.os_adapter,
        }

    def execute_plan(self, plan: ActionPlan) -> List[ExecutionResult]:
        """
        Executes action plan.

        Args:
            plan: Plan to execute

        Returns:
            List of results for each action
        """
        if plan.is_empty:
            return []
        
        if plan.dry_run:
            return self._simulate_plan(plan)
        
        results: List[ExecutionResult] = []
        
        for action in plan.actions:
            result = self._execute_action(action)
            results.append(result)

            # Stop on error if configured
            if not result.is_success and self.config.stop_on_first_error:
                # Add CANCELLED for remaining actions
                remaining = plan.actions[len(results):]
                for remaining_action in remaining:
                    results.append(ExecutionResult(
                        action=remaining_action,
                        status=ExecutionStatus.CANCELLED,
                        error="Cancelled due to previous error",
                    ))
                break
        
        return results

    def execute_single(self, action: Action) -> ExecutionResult:
        """Executes a single action."""
        return self._execute_action(action)

    def _execute_action(self, action: Action) -> ExecutionResult:
        """Executes a single action with validation."""
        start_time = datetime.now(timezone.utc)
        
        # Pre-execution validation
        if self.config.validate_before_execution:
            validation = self.validator.validate_action(action)
            if not validation.allowed:
                return ExecutionResult(
                    action=action,
                    status=ExecutionStatus.DENIED,
                    error=validation.reason,
                    started_at=start_time,
                    completed_at=datetime.now(timezone.utc),
                )
        
        try:
            # Retrieve handler
            handler = self._tool_handlers.get(action.tool_name)
            if handler is None:
                return ExecutionResult(
                    action=action,
                    status=ExecutionStatus.FAILED,
                    error=f"Unknown tool: {action.tool_name}",
                    started_at=start_time,
                    completed_at=datetime.now(timezone.utc),
                )

            # Retrieve method
            method = getattr(handler, action.function_name, None)
            if method is None:
                return ExecutionResult(
                    action=action,
                    status=ExecutionStatus.FAILED,
                    error=f"Unknown function: {action.function_name}",
                    started_at=start_time,
                    completed_at=datetime.now(timezone.utc),
                )
            
            # Execute action
            logger.info(f"Executing: {action.to_human_readable()}")
            output = method(**action.args)

            # Cut output if needed
            if self.config.log_outputs and output is not None:
                output_str = str(output)
                if len(output_str) > self.config.max_output_length:
                    output = output_str[:self.config.max_output_length] + "... [truncated]"
            
            return ExecutionResult(
                action=action,
                status=ExecutionStatus.SUCCESS,
                output=output,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )
            
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return ExecutionResult(
                action=action,
                status=ExecutionStatus.DENIED,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return ExecutionResult(
                action=action,
                status=ExecutionStatus.FAILED,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.exception(f"Execution error: {e}")
            return ExecutionResult(
                action=action,
                status=ExecutionStatus.FAILED,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )

    def _simulate_plan(self, plan: ActionPlan) -> List[ExecutionResult]:
        """Simulates execution of the plan (dry run)."""
        results = []
        
        for action in plan.actions:
            # Validation works in dry run
            if self.config.validate_before_execution:
                validation = self.validator.validate_action(action)
                if not validation.allowed:
                    results.append(ExecutionResult(
                        action=action,
                        status=ExecutionStatus.DENIED,
                        error=f"[DRY RUN] Would be denied: {validation.reason}",
                    ))
                    continue
            
            results.append(ExecutionResult(
                action=action,
                status=ExecutionStatus.DRY_RUN,
                output=f"[DRY RUN] Would execute: {action.to_human_readable()}",
            ))
        
        return results


# ============================================
# Result Formatters
# ============================================

class ExecutionResultFormatter:
    """Formats execution results for UI."""

    @staticmethod
    def to_text(results: List[ExecutionResult]) -> str:
        """Formats results as text."""
        if not results:
            return "No actions executed."
        
        lines = ["Execution Results:", ""]
        
        for i, result in enumerate(results, 1):
            status_emoji = {
                ExecutionStatus.SUCCESS: "✅",
                ExecutionStatus.FAILED: "❌",
                ExecutionStatus.DENIED: "⛔",
                ExecutionStatus.CANCELLED: "⏹️",
                ExecutionStatus.DRY_RUN: "🔍",
            }.get(result.status, "❓")
            
            lines.append(f"{i}. {status_emoji} {result.action.description}")
            lines.append(f"   Status: {result.status.value}")
            
            if result.output:
                output_preview = str(result.output)[:200]
                if len(str(result.output)) > 200:
                    output_preview += "..."
                lines.append(f"   Output: {output_preview}")
            
            if result.error:
                lines.append(f"   Error: {result.error}")
            
            if result.duration_ms:
                lines.append(f"   Duration: {result.duration_ms:.1f}ms")
            
            lines.append("")
        
        # Summary
        success_count = sum(1 for r in results if r.is_success)
        total = len(results)
        lines.append(f"Summary: {success_count}/{total} actions successful")
        
        return "\n".join(lines)

    @staticmethod
    def to_dict(results: List[ExecutionResult]) -> Dict[str, Any]:
        """Formats results as a dictionary."""
        return {
            "total": len(results),
            "successful": sum(1 for r in results if r.is_success),
            "results": [
                {
                    "action_id": r.action.action_id,
                    "description": r.action.description,
                    "status": r.status.value,
                    "output": str(r.output)[:1000] if r.output else None,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }
