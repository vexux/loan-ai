import networkx as nx
from typing import Dict, Any


class PolicyGraph:
    """
    A generic, domain-agnostic in-memory Knowledge Graph using NetworkX.
    Contains NO domain data. Rules are loaded externally by the domain layer.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_product_node(self, name: str) -> None:
        """Register a product/entity (e.g., 'Home Loan', 'Car Insurance')."""
        self.graph.add_node(name, type="Product")

    def add_constraint_node(self, value: str, node_type: str = "Constraint") -> None:
        """Register a constraint value node (e.g., '700', '50000')."""
        self.graph.add_node(value, type=node_type)

    def add_rule(self, product: str, constraint_value: str, relation: str) -> None:
        """Add a directed rule edge from a product to a constraint value."""
        self.graph.add_edge(product, constraint_value, relation=relation)

    @staticmethod
    def _parse_canonical_value(val: Any) -> Any:
        """
        Permanently converts string representations into native Python types.
        Handles integers, floating points, booleans, and clean strings safely.
        """
        if not isinstance(val, str):
            return val

        cleaned = val.strip()

        # 1. Boolean check
        if cleaned.lower() == "true":
            return True
        if cleaned.lower() == "false":
            return False

        # 2. Integer check
        try:
            return int(cleaned)
        except ValueError:
            pass

        # 3. Float check (e.g. interest rates, decimal ratios)
        try:
            return float(cleaned)
        except ValueError:
            pass

        # 4. Standard string
        return cleaned

    def query_policy(self, entity: str) -> Dict[str, Any]:
        """
        Traverse the graph and return all rules for the given entity.
        Also always includes universal blanket rules from 'Any' node.
        """
        if entity not in self.graph:
            return {"error": f"Entity '{entity}' not found in Knowledge Graph."}

        rules = {}

        # 1. Get specific rules for the requested entity
        for _, target, data in self.graph.out_edges(entity, data=True):
            relation = data.get("relation")
            if relation:
                rules[relation] = self._parse_canonical_value(target)

        # 2. Always include universal blanket rules from 'Any'
        if "Any" in self.graph:
            for _, target, data in self.graph.out_edges("Any", data=True):
                relation = data.get("relation")
                if relation:
                    rules[relation] = self._parse_canonical_value(target)

        return rules

    def list_products(self) -> list[str]:
        """Return all registered product/entity node names."""
        return [
            n for n, d in self.graph.nodes(data=True)
            if d.get("type") == "Product"
        ]
