import json
from components.knowledge_graph.graph_engine import PolicyGraph


class GraphDataAdapter:
    """
    Domain-agnostic adapter that lets the Tool Registry query a PolicyGraph.
    The graph is injected from outside (built by the domain layer).
    """

    def __init__(self, graph: PolicyGraph) -> None:
        self.graph = graph

    def execute(self, query: str) -> str:
        """
        Queries the knowledge graph. Detects the entity from the query string
        by matching against registered product nodes in the graph.
        """
        query_lower = query.lower()

        matched_entity = None
        for product in self.graph.list_products():
            if product.lower() in query_lower:
                matched_entity = product
                break

        if not matched_entity:
            return (
                f"Error: Could not identify a known entity in the query. "
                f"Available: {self.graph.list_products()}"
            )

        results = self.graph.query_policy(matched_entity)
        return json.dumps(results, indent=2)
