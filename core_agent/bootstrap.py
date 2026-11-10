import os
from components.model_gateway import (
    create_local_model_gateway,
    create_gguf_model_gateway,
)
from components.tool_registry.registry_factory import create_tool_registry
from components.tool_registry.capability import CapabilityDefinition
from domain.banking.handlers import banking_loan_application_handler
from components.memory.in_memory_store import InMemoryMemoryStore
from components.policy.policy_engine import RuleBasedPolicyEngine
from components.workflow.workflow_engine import WorkflowEngine
from components.observability.tracer import StructuredTracer
from components.data_adapters.sqlite_adapter import SQLiteDataAdapter

from domain.banking.workflows import (
    create_loan_eligibility_workflow,
    create_loan_application_workflow,
    create_account_summary_workflow,
    create_list_loan_applications_workflow,
    create_policy_inquiry_workflow
)


from core_agent.agent import Agent
from core_agent.decision.llm_decision_engine import LLMDecisionEngine
from core_agent.execution.registry_execution_controller import RegistryExecutionController
from core_agent.intent.semantic_router import SemanticRouter
from sentence_transformers import SentenceTransformer
from core_agent.observation.observer import ExecutionObserver
from core_agent.planning.llm_planner import LLMPlanner
from core_agent.reasoning.llm_reasoning_engine import LLMReasoningEngine
from components.knowledge_graph.graph_adapter import GraphDataAdapter
from domain.banking.policy_graph import create_banking_policy_graph



# ============================================================================
# LOCAL MODEL CONFIGURATION (Switch here anytime)
# ============================================================================
MODEL_NAME = "Llama-3.2-3B-Instruct"
GGUF_MODEL_PATH = r"C:\NATWEST\slm-project\models\Llama-3.2-3B-Instruct-Q4_K_M.gguf"
# ============================================================================


def create_llm_agent() -> Agent:
    # 1. Infrastructure (reads strictly from local disk cache)
    # model_gateway = create_local_model_gateway(
    #     model_id=MODEL_NAME,
    #     source=MODEL_SOURCE,
    # )
    # 1. Instantiate GGUF Model Gateway
    model_gateway = create_gguf_model_gateway(
        model_path=GGUF_MODEL_PATH,
        n_ctx=4096,
    )
    # Build banking policy graph (domain layer provides the rules)
    policy_graph = create_banking_policy_graph()
    graph_adapter = GraphDataAdapter(graph=policy_graph)

    tool_registry = create_tool_registry(model_gateway, MODEL_NAME, graph_adapter=graph_adapter)
    tool_registry.register(CapabilityDefinition(
        action="submit_loan_application",
        name="banking_loan_submission",
        description="Persist loan application and audit event transaction",
        domain="banking",
        handler=banking_loan_application_handler,
    ))


    memory_store = InMemoryMemoryStore()
    policy_engine = RuleBasedPolicyEngine(
        allowed_actions=tool_registry.get_available_actions()
    )
    tracer = StructuredTracer(log_dir="logs/traces")

    workflow_engine = WorkflowEngine(
        tool_registry=tool_registry,
        tracer=tracer,
    )

    workflow_engine.register(create_policy_inquiry_workflow()) 
    workflow_engine.register(create_loan_eligibility_workflow())
    workflow_engine.register(create_list_loan_applications_workflow())   # ← before submission
    workflow_engine.register(create_account_summary_workflow())
    workflow_engine.register(create_loan_application_workflow())          # ← submission last


    # 2. Reasoning & Cognitive Core
    # 2. Semantic Router — reuses the same embedding model already loaded for RAG
    # No extra model download. Zero LLM inference at routing time (~1ms per query).
    router_encoder = SentenceTransformer(
        "all-MiniLM-L6-v2",
        device="cpu",
    )

    workflow_descriptions = {
        wf.workflow_id: wf.description
        for wf in workflow_engine.get_all_workflows()
        if getattr(wf, "description", "")
    }
    workflow_primary_intents = {
        wf.workflow_id: wf.primary_intent
        for wf in workflow_engine.get_all_workflows()
        if getattr(wf, "primary_intent", "")
    }

    workflow_trigger_phrases = {
        wf.workflow_id: list(getattr(wf, "trigger_intents", []))
        if not getattr(wf, "is_write_operation", False)
        else []
        for wf in workflow_engine.get_all_workflows()
    }

    intent_detector = SemanticRouter(
        encoder=router_encoder,
        workflow_descriptions=workflow_descriptions,
        workflow_primary_intents=workflow_primary_intents,
        workflow_trigger_phrases=workflow_trigger_phrases,
        threshold=0.40,
    )

    planner = LLMPlanner(
        model_gateway=model_gateway,
        available_actions=tool_registry.get_available_actions(),
        action_descriptions=tool_registry.get_action_descriptions(),
        model_name=MODEL_NAME,
    )

    reasoning_engine = LLMReasoningEngine(
        model_gateway=model_gateway,
        tool_registry=tool_registry,
        model_name=MODEL_NAME,
    )

    decision_engine = LLMDecisionEngine(
        tool_registry=tool_registry,
    )

    execution_controller = RegistryExecutionController(
        tool_registry=tool_registry,
    )
    observer = ExecutionObserver()

    db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "banking.db")
    )

    # 4. Assemble Agent
    return Agent(
        intent_detector=intent_detector,
        planner=planner,
        reasoning_engine=reasoning_engine,
        decision_engine=decision_engine,
        execution_controller=execution_controller,
        observer=observer,
        memory=memory_store,
        policy_engine=policy_engine,
        workflow_engine=workflow_engine,
        tracer=tracer,
    )