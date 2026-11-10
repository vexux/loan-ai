import asyncio
from typing import Any, Optional

from contracts.common.enums import ComponentType, ExecutionStatus
from contracts.common.execution_result import ExecutionResult
from contracts.component.component_metadata import ComponentMetadata
from contracts.component.health_status import HealthStatus
from contracts.observability.observability_contract import ObservabilityContract
from contracts.workflow.workflow_contract import (
    WorkflowContract,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStep,
)
from components.tool_registry.tool_registry import ToolRegistry
from components.workflow.workflow_definition import EnhancedWorkflowStep, WorkflowDefinition


class WorkflowEngine(WorkflowContract):
    """
    Domain-agnostic Workflow Engine with Parallel Execution Batches,
    Conditional Step Evaluation, and Span Tracing.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tracer: Optional[ObservabilityContract] = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.tracer = tracer
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        missing = [
            s.action for s in workflow.steps
            if s.action and not self.tool_registry.find_by_action(s.action)
        ]
        if missing:
            raise ValueError(
                f"Workflow '{workflow.workflow_id}' references unknown actions: {missing}. "
                f"Register these capabilities in the ToolRegistry before registering the workflow."
            )
        self._workflows[workflow.workflow_id] = workflow

    def get_all_workflows(self) -> list[WorkflowDefinition]:
        return list(self._workflows.values())

    def get_intent_workflow_map(self) -> dict[str, str]:
        return {
            wf.primary_intent: wf.workflow_id
            for wf in self._workflows.values()
            if wf.primary_intent
        }

    def get_intent_vocabulary(self) -> list[str]:
        return [wf.primary_intent for wf in self._workflows.values() if wf.primary_intent]

    def get_workflow_by_id(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._workflows.get(workflow_id)

    def get_write_workflow(self) -> WorkflowDefinition | None:
        return next(
            (wf for wf in self._workflows.values() if wf.is_write_operation),
            None,
        )

    def get_steps(self, workflow_name: str) -> list[WorkflowStep]:
        wf = self._workflows.get(workflow_name)
        if not wf:
            return []
        return [
            WorkflowStep(
                step_id=s.step_id,
                name=s.name or s.step_id,
                component_name="ToolRegistry",
                action=s.action,
                parameters=s.inputs,
            )
            for s in wf.steps
        ]

    def can_execute(self, request: WorkflowRequest) -> bool:
        return request.workflow_name in self._workflows

    async def execute(self, request: WorkflowRequest) -> ExecutionResult[WorkflowResponse]:
        wf = self._workflows.get(request.workflow_name)
        if not wf:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILURE,
                data=WorkflowResponse(
                    workflow_name=request.workflow_name,
                    successful=False,
                    message=f"Workflow '{request.workflow_name}' not registered.",
                ),
            )

        executed_steps: list[WorkflowStep] = []
        step_outputs: dict[str, Any] = {}
        accumulated_context_parts: list[str] = []

        batches = self._build_execution_batches(wf)

        for batch in batches:
            if len(batch) == 1:
                step = batch[0]
                res = await self._run_step(step, request, step_outputs, accumulated_context_parts)
                if not res["success"]:
                    return ExecutionResult(
                        success=False,
                        status=ExecutionStatus.FAILURE,
                        data=WorkflowResponse(
                            workflow_name=wf.workflow_id,
                            successful=False,
                            executed_steps=executed_steps,
                            message=f"Workflow failed at step '{step.step_id}': {res.get('error')}",
                        ),
                    )
                executed_steps.append(res["workflow_step"])
            else:
                tasks = [
                    self._run_step(step, request, step_outputs, accumulated_context_parts)
                    for step in batch
                ]
                results = await asyncio.gather(*tasks)

                for step, res in zip(batch, results):
                    if not res["success"]:
                        return ExecutionResult(
                            success=False,
                            status=ExecutionStatus.FAILURE,
                            data=WorkflowResponse(
                                workflow_name=wf.workflow_id,
                                successful=False,
                                executed_steps=executed_steps,
                                message=f"Workflow failed at parallel step '{step.step_id}': {res.get('error')}",
                            ),
                        )
                    executed_steps.append(res["workflow_step"])

        final_response_content = step_outputs.get("final_content", "Workflow completed successfully.")

        return ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            data=WorkflowResponse(
                workflow_name=wf.workflow_id,
                successful=True,
                executed_steps=executed_steps,
                output=step_outputs,
                message=final_response_content,
            ),
        )

    def _build_execution_batches(self, wf: WorkflowDefinition) -> list[list[EnhancedWorkflowStep]]:
        batches: list[list[EnhancedWorkflowStep]] = []
        completed_step_ids: set[str] = set()
        remaining_steps = list(wf.steps)

        while remaining_steps:
            ready = [
                s for s in remaining_steps
                if all(dep in completed_step_ids for dep in s.dependencies)
            ]
            if not ready:
                raise ValueError(
                    f"Unresolvable dependencies in workflow '{wf.workflow_id}'. "
                    f"Remaining stalled steps: {[s.step_id for s in remaining_steps]}"
                )

            parallel_groups: dict[str, list[EnhancedWorkflowStep]] = {}
            sequential_ready: list[EnhancedWorkflowStep] = []

            for s in ready:
                if s.parallel_group:
                    parallel_groups.setdefault(s.parallel_group, []).append(s)
                else:
                    sequential_ready.append(s)

            if parallel_groups:
                for grp_name, group_steps in parallel_groups.items():
                    batches.append(group_steps)
                    for gs in group_steps:
                        completed_step_ids.add(gs.step_id)
                        remaining_steps.remove(gs)
            elif sequential_ready:
                single_step = sequential_ready[0]
                batches.append([single_step])
                completed_step_ids.add(single_step.step_id)
                remaining_steps.remove(single_step)

        return batches

    async def _run_step(
        self,
        step: EnhancedWorkflowStep,
        request: WorkflowRequest,
        step_outputs: dict[str, Any],
        accumulated_context_parts: list[str],
    ) -> dict[str, Any]:
        capability = self.tool_registry.find_by_action(step.action)
        if not capability or not capability.handler:
            return {"success": False, "error": f"Capability handler not found for action '{step.action}'."}

        merged_inputs = dict(step.inputs)
        merged_inputs.update(request.input)
        merged_inputs.update(step_outputs)

        if accumulated_context_parts:
            merged_inputs["context"] = "\n\n".join(accumulated_context_parts)

        # Evaluate step condition if defined
        if step.condition is not None and callable(step.condition):
            try:
                should_run = step.condition(merged_inputs)
            except Exception as cond_err:
                return {"success": False, "error": f"Condition evaluation failed for step '{step.step_id}': {cond_err}"}

            if not should_run:
                step_outputs[step.step_id] = {"status": "skipped", "message": f"Step '{step.step_id}' skipped by condition."}
                return {
                    "success": True,
                    "skipped": True,
                    "workflow_step": WorkflowStep(
                        step_id=step.step_id,
                        name=step.name or step.step_id,
                        component_name="ToolRegistry",
                        action=step.action,
                        parameters=merged_inputs,
                    ),
                    "output": step_outputs[step.step_id],
                }

        trace_id = request.context.request_id if request.context else "TRC-WORKFLOW"

        sanitized_meta = {}
        for k, v in merged_inputs.items():
            if (k.endswith("_id") or k == "id" or k == "resource") and isinstance(v, (str, int)):
                sanitized_meta[k] = str(v)

        if self.tracer:
            async with self.tracer.span(
                trace_id=trace_id,
                component="WorkflowEngine",
                operation=step.step_id,
                metadata=sanitized_meta,
            ):
                result_dict = await capability.handler(merged_inputs)
        else:
            result_dict = await capability.handler(merged_inputs)

        step_outputs[step.step_id] = result_dict
        if isinstance(result_dict, dict):
            if "data" in result_dict and isinstance(result_dict["data"], dict):
                step_outputs.update(result_dict["data"])
            if "content" in result_dict and result_dict["content"]:
                accumulated_context_parts.append(str(result_dict["content"]))
                step_outputs["final_content"] = result_dict["content"]

        return {
            "success": True,
            "workflow_step": WorkflowStep(
                step_id=step.step_id,
                name=step.name or step.step_id,
                component_name="ToolRegistry",
                action=step.action,
                parameters=merged_inputs,
            ),
            "output": result_dict,
        }

    async def get_metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="WorkflowEngine",
            type=ComponentType.WORKFLOW,
            version="2.1.0",
            capabilities=list(self._workflows.keys()),
        )

    async def get_health(self) -> HealthStatus:
        return HealthStatus(healthy=True, message=f"WorkflowEngine ready with {len(self._workflows)} workflows.")

    async def health_check(self) -> bool:
        return True
