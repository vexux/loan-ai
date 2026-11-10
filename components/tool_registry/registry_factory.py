from components.tool_registry.tool_registry import ToolRegistry
from components.tool_registry.capability import CapabilityDefinition
from components.tool_registry.generic_handlers import (
    generic_knowledge_search_handler,
    generic_resource_query_handler,
    generic_resource_filter_handler, 
    generic_resource_create_handler,
    generic_transaction_handler,
    create_response_generator_handler,
    create_knowledge_graph_handler,
)


def create_tool_registry(
    model_gateway,
    model_name: str,
    graph_adapter=None,
) -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(CapabilityDefinition(
        action="search_documents",
        name="document_search",
        description="Search documents and knowledge base for relevant information",
        domain="generic",
        handler=generic_knowledge_search_handler,
    ))

    registry.register(CapabilityDefinition(
        action="retrieve_entity",
        name="entity_retrieval",
        description="Retrieve a structured record or entity by identifier",
        domain="generic",
        handler=generic_resource_query_handler,
    ))

    registry.register(CapabilityDefinition(
        action="query_records",
        name="record_filter_query",
        description="Query a database table with column filters, returns ALL matching rows (e.g. all loans for a customer)",
        domain="generic",
        handler=generic_resource_filter_handler,
    ))

    registry.register(CapabilityDefinition(
        action="create_entity",
        name="entity_creation",
        description="Create a single new record in a database resource",
        domain="generic",
        handler=generic_resource_create_handler,
    ))

    registry.register(CapabilityDefinition(
        action="execute_transaction",
        name="atomic_transaction",
        description="Execute multiple write operations in an atomic all-or-nothing transaction",
        domain="generic",
        handler=generic_transaction_handler,
    ))

    registry.register(CapabilityDefinition(
        action="generate_response",
        name="response_generation",
        description="Synthesize a final natural language answer from retrieved context",
        domain="generic",
        handler=create_response_generator_handler(model_gateway, model_name),
    ))

    if graph_adapter:
        registry.register(CapabilityDefinition(
            action="query_policy_graph",
            name="policy_graph_query",
            description="Retrieve exact deterministic constraints and limits",
            domain="generic",
            handler=create_knowledge_graph_handler(graph_adapter),
        ))

    return registry
