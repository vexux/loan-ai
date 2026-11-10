import re
import time
from typing import Optional
from uuid import uuid4

from contracts.common.request_context import RequestContext
from contracts.memory.memory_contract import MemoryContract, MemoryRecord
from contracts.observability.observability_contract import ObservabilityContract
from contracts.policy import PolicyContract, PolicyRequest
from contracts.workflow import WorkflowRequest
from core_agent.cli_ui import Spinner

from components.workflow.workflow_engine import WorkflowEngine
from core_agent.decision.decision_engine import DecisionEngine
from core_agent.execution.execution_controller import ExecutionController
from core_agent.intent.intent_detector import IntentDetector
from core_agent.models.agent_request import AgentRequest
from core_agent.models.agent_response import AgentResponse
from core_agent.models.execution_state import ExecutionState, StepExecutionResult
from core_agent.models.decision import Decision
from core_agent.observation.observer import Observer
from core_agent.planning.planner import Planner
from core_agent.identity.identity_resolver import IdentityResolver
from core_agent.reasoning.reasoning_engine import ReasoningEngine
from components.policy.input_guardrails import InputGuardrails
from components.policy.output_guardrails import OutputGuardrails
from components.policy.rbac import RBACPolicyEngine


class Agent:
    def __init__(
        self,
        intent_detector: IntentDetector,
        planner: Planner,
        reasoning_engine: ReasoningEngine,
        decision_engine: DecisionEngine,
        execution_controller: ExecutionController,
        observer: Observer,
        memory: Optional[MemoryContract] = None,
        policy_engine: Optional[PolicyContract] = None,
        workflow_engine: Optional[WorkflowEngine] = None,
        tracer: Optional[ObservabilityContract] = None,
        input_guardrails: Optional[InputGuardrails] = None,
        output_guardrails: Optional[OutputGuardrails] = None,
        rbac_engine: Optional[RBACPolicyEngine] = None,
        max_iterations: int = 10,
    ):
        self.intent_detector = intent_detector
        self.planner = planner
        self.reasoning_engine = reasoning_engine
        self.decision_engine = decision_engine
        self.execution_controller = execution_controller
        self.observer = observer
        self.memory = memory
        self.policy_engine = policy_engine
        self.workflow_engine = workflow_engine
        self.tracer = tracer
        # Use injected instances; only fall back to defaults when nothing was passed.
        self.input_guardrails = input_guardrails if input_guardrails is not None else InputGuardrails()
        self.output_guardrails = output_guardrails if output_guardrails is not None else OutputGuardrails()
        self.rbac_policy = rbac_engine if rbac_engine is not None else RBACPolicyEngine()
        self.max_iterations = max_iterations


    async def run(self, request: AgentRequest) -> AgentResponse:
        context = request.context or self._create_context(request)
        trace_id = f"TRC-{uuid4().hex[:8]}"
        context.request_id = trace_id

        state = ExecutionState(request_id=trace_id, max_iterations=self.max_iterations)
        state.original_message = request.message
        start_time = time.perf_counter()

        # 0. Dialogue History
        history_str = ""
        if self.memory and context.session_id:
            history_str = await self.memory.get_dialogue_history(context.session_id, limit=2)

        # 0.5 Input Guardrails
        decision, sanitized_msg = self.input_guardrails.evaluate_input(request.message)
        if not decision.allowed:
            return AgentResponse(request_id=trace_id, message=decision.reasons[0], success=False)
        request.message = sanitized_msg

        try:
            print("\n[PROCESSING]")
            intent_spinner = Spinner("[1/4] Analyzing query and understanding intent (Local SLM)...")
            intent_spinner.start()

            # 1. INTENT
            if self.tracer:
                async with self.tracer.span(trace_id, "IntentDetector", "detect") as span:
                    understanding = await self.intent_detector.detect(request.message, history=history_str)
                    span.decision = {"intent": understanding.intent, "confidence": understanding.confidence}
            else:
                understanding = await self.intent_detector.detect(request.message, history=history_str)

            state.understanding = understanding
            await intent_spinner.stop(success=True, custom_text="[1/4] Query analyzed and intent classified")



            # 2. PLAN (Workflow Matching & Target Resolution)
            matched_wf = None
            if self.workflow_engine:
                intent_lower = (understanding.intent or "").lower()
                query_lower = request.message.lower()

                # A. Submission verbs priority — only imperative/declarative, NOT interrogative
                query_words = set(re.findall(r"\b\w+\b", query_lower))
                _has_submission_verb = bool(query_words.intersection({"apply", "submit", "file"}))
                _is_interrogative = bool(query_words.intersection({"can", "could", "should", "would", "how", "what", "is", "do", "does"}))
                if _has_submission_verb and not _is_interrogative:
                    matched_wf = self.workflow_engine.get_write_workflow()

                # B. Primary intent → workflow lookup (router already gave us the right intent)
                if not matched_wf:
                    intent_map = self.workflow_engine.get_intent_workflow_map()
                    wf_id = intent_map.get(intent_lower)
                    if wf_id:
                        matched_wf = self.workflow_engine.get_workflow_by_id(wf_id)


                #    # C. Trigger phrase scan — can override Step B but NEVER Step A
                #     candidates = []
                #     for wf in self.workflow_engine.get_all_workflows():
                #         triggers = [t.lower() for t in getattr(wf, "trigger_intents", [])]
                #         for t in triggers:
                #             if t == intent_lower or re.search(r'\b' + re.escape(t) + r'\b', query_lower):
                #                 candidates.append((len(t), wf))
                #                 break
                #     if candidates:
                #         candidates.sort(key=lambda x: x[0], reverse=True)
                #         trigger_wf = candidates[0][1]
                #         # Override Step B if trigger found a different, more specific workflow
                #         if not matched_wf or (trigger_wf.workflow_id != matched_wf.workflow_id and candidates[0][0] > 3):
                #             matched_wf = trigger_wf

            # 2. RESOLVE IDENTITY & PREPARE INPUTS (Domain-Agnostic)
            is_self_op = bool(matched_wf and matched_wf.is_self_operation)
            is_write_op = bool(matched_wf and matched_wf.is_write_operation)

            target_id, resolved_inputs = IdentityResolver.resolve_target(
                query=request.message,
                context=context,
                entities=understanding.entities,
                is_self_operation=is_self_op,
                is_write_operation=is_write_op,
            )

            wf_inputs = {
                **resolved_inputs,
                "original_query": request.message,
                "history": history_str,
            }

            if matched_wf:
                plan = self.planner.plan_from_workflow(matched_wf, wf_inputs)
            else:
                plan = await self.planner.plan(understanding)

            state.plan = plan

            # GUEST GATE: Unauthenticated sessions may run public workflows or generic hypothetical queries
            _is_guest = (context.metadata.get("role") == "guest")
            if _is_guest and matched_wf and getattr(matched_wf, "requires_auth", False):
                # Exception: loan_eligibility_check without target_id is a general hypothetical calculation
                is_hypothetical_check = (matched_wf.workflow_id == "loan_eligibility_check" and not target_id)
                if not is_hypothetical_check:
                    return AgentResponse(
                        request_id=trace_id,
                        message="Please log in first to access personalised services. Use /login <your_customer_id>.",
                        success=False,
                    )

            workflow_label = matched_wf.name if matched_wf else "Ad-hoc Dynamic Plan"
            print(f"  ✔ [2/4] Intent: '{matched_wf.primary_intent if matched_wf else understanding.intent}' | Plan: {len(state.plan.steps)} step(s) ({workflow_label})")            
            # 3. UNIFIED EXECUTION LOOP
            exec_spinner = Spinner("[3/4] Executing plan & synthesizing response...")
            exec_spinner.start()
            
            while not state.is_finished():
                state.iteration += 1


                # Select next uncompleted plan step
                current_step = None
                for step in state.plan.steps:
                    if step.step_id not in state.completed_steps:
                        current_step = step
                        break
                state.current_step = current_step

                if current_step is None:
                    state.completed = True
                    break

                # Prepare step inputs
                step_inputs = dict(current_step.inputs)
                step_inputs["original_query"] = state.original_message
                step_inputs["history"] = history_str
                if target_id and "id" not in step_inputs:
                    step_inputs["id"] = target_id
                    step_inputs["target_id"] = target_id

                # Accumulate context and structured data from earlier steps
                context_parts = []
                for r in state.step_results.values():
                    if r.success and r.output:
                        if isinstance(r.output, dict):
                            if "content" in r.output and r.output["content"]:
                                context_parts.append(str(r.output["content"]))
                            if "data" in r.output and isinstance(r.output["data"], dict):
                                step_inputs.update({
                                    k: v for k, v in r.output["data"].items() if k != "context"
                                })
                        else:
                            context_parts.append(str(r.output))

                if context_parts:
                    step_inputs["context"] = "\n\n".join(context_parts)
                # Conditional Step Evaluation: Skip step cleanly if condition evaluates to False
                if current_step.condition is not None and callable(current_step.condition):
                    try:
                        should_run = current_step.condition(step_inputs)
                    except Exception as cond_err:
                        state.failed = True
                        state.failure_reason = f"Condition evaluation failed for step '{current_step.step_id}': {cond_err}"
                        break

                    if not should_run:
                        step_result = StepExecutionResult(
                            step_id=current_step.step_id,
                            action=current_step.action,
                            success=True,
                            output={"status": "skipped", "message": f"Step '{current_step.step_id}' skipped by condition."},
                        )
                        state.record_step_result(step_result)
                        state.completed_steps.append(current_step.step_id)
                        continue


                # Create Step Decision
                raw_decision = Decision(
                    action=current_step.action,
                    inputs=step_inputs,
                    rationale=f"Executing plan step '{current_step.step_id}'",
                    confidence=1.0,
                )

                # DECIDE: Resolve capability via DecisionEngine
                step_decision = await self.decision_engine.select_capability(raw_decision)

                # RBAC Authorization Check
                if self.rbac_policy:
                    rbac_res = self.rbac_policy.evaluate_access(context, current_step.action, target_id)
                    if not rbac_res.allowed:
                        return AgentResponse(
                            request_id=trace_id,
                            message=f"[SECURITY - RBAC] {rbac_res.reasons[0]}",
                            success=False,
                        )

                                # EXECUTE: Dispatch capability via ExecutionController
                if self.tracer:
                    async with self.tracer.span(trace_id, "ExecutionController", current_step.step_id):
                        exec_output = await self.execution_controller.execute(step_decision)
                else:
                    exec_output = await self.execution_controller.execute(step_decision)
                is_success = isinstance(exec_output, dict) and exec_output.get("status") == "success"

                
                step_result = StepExecutionResult(
                    step_id=current_step.step_id,
                    action=current_step.action,
                    success=is_success,
                    output=exec_output,
                    error=exec_output.get("error") if isinstance(exec_output, dict) else None,
                )

                # OBSERVE: Inspect outcome and data quality
                observation = await self.observer.observe(step_result)
                step_result.observed_successful = observation.successful
                step_result.observed_sufficient = observation.sufficient
                state.record_step_result(step_result)
                # Dynamic Owner Binding & RBAC Enforcement (prevents name-based RBAC bypass)
                if not target_id and is_success and isinstance(exec_output, dict):
                    data_block = exec_output.get("data", {})
                    if isinstance(data_block, dict):
                        for k, v in data_block.items():
                            if k.endswith("_id") and k not in {"request_id", "session_id", "trace_id", "span_id"}:
                                target_id = str(v)
                                break
                    if target_id and self.rbac_policy:
                        post_rbac = self.rbac_policy.evaluate_access(context, current_step.action, target_id)
                        if not post_rbac.allowed:
                            return AgentResponse(
                                request_id=trace_id,
                                message=f"[SECURITY - RBAC] {post_rbac.reasons[0]}",
                                success=False,
                            )


                if not observation.successful:
                    state.failed = True
                    state.failure_reason = observation.message
                    break

            await exec_spinner.stop(success=state.is_successful(), custom_text="[3/4] Plan executed & response synthesized")
            print("  ✔ [4/4] Safety guardrails verified & audit trace finalized\n", flush=True)

            # 4. Final Output Synthesis & Guardrails
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            final_message = self._format_response(state)

            if self.output_guardrails:
                _, final_message = self.output_guardrails.evaluate_output(final_message)

            trace_file = await self._finalize_trace(trace_id, "SUCCESS" if state.is_successful() else "FAILED")

            # 5. Save Conversation Memory
            if self.memory:
                await self.memory.save(MemoryRecord(
                    memory_id=str(uuid4()),
                    content=request.message,
                    session_id=context.session_id,
                    user_id=context.user_id,
                    metadata={"speaker": "User"},
                ))
                await self.memory.save(MemoryRecord(
                    memory_id=str(uuid4()),
                    content=final_message,
                    session_id=context.session_id,
                    user_id=context.user_id,
                    metadata={"speaker": "Agent"},
                ))

            return AgentResponse(
                request_id=trace_id,
                message=final_message,
                success=state.is_successful(),
                intent=understanding.intent,
                metadata={
                    "iterations": state.iteration,
                    "plan": state.plan,
                    "trace_file": trace_file,
                    "latency_ms": elapsed_ms,
                    "trace_id": trace_id,
                },
            )

        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            trace_file = await self._finalize_trace(trace_id, "FAILED")
            return AgentResponse(
                request_id=trace_id,
                message=f"[ERROR] {exc}",
                success=False,
                intent=state.understanding.intent if state.understanding else "unknown",
                metadata={"latency_ms": elapsed_ms, "trace_file": trace_file},
            )



    async def _finalize_trace(self, trace_id: str, status: str) -> Optional[str]:
        if self.tracer:
            trace = self.tracer.get_trace(trace_id)
            if trace:
                trace.status = status
                return await self.tracer.save_trace(trace)
        return None

    @staticmethod
    def _format_response(state: ExecutionState) -> str:
        last_result = state.get_last_result()
        if last_result and last_result.success:
            if isinstance(last_result.output, dict):
                return last_result.output.get("content", str(last_result.output))
            return str(last_result.output)
        if state.failure_reason:
            return f"[ERROR] Execution failed: {state.failure_reason}"
        return "[ERROR] Plan was created, but no steps were executed."

    @staticmethod
    def _create_context(request: AgentRequest) -> RequestContext:
        req_id = f"REQ-{uuid4().hex[:8]}"
        # BUG 5 FIX: Reuse the session_id and user_id from the incoming request if they exist.
        # Before this fix, a brand-new random session_id was generated on every call, which
        # meant memory.get_dialogue_history() always returned empty — the history was saved
        # under a different session_id than the one used to retrieve it next turn.
        existing_ctx = request.context
        session_id = (
            (existing_ctx.session_id if existing_ctx and existing_ctx.session_id else None)
            or f"SESS-{uuid4().hex[:8]}"
        )
        user_id = (
            (existing_ctx.user_id if existing_ctx and existing_ctx.user_id else None)
            or "anonymous"
        )
        return RequestContext(
            request_id=req_id,
            correlation_id=req_id,
            session_id=session_id,
            user_id=user_id,
            tenant_id="default",
        )