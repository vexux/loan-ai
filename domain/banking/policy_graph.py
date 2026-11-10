from components.knowledge_graph.graph_engine import PolicyGraph


def create_banking_policy_graph() -> PolicyGraph:
    """
    Builds and returns a PolicyGraph populated with ICICI banking domain rules.
    All domain knowledge lives here — the engine itself stays generic.
    """
    graph = PolicyGraph()

    # --- Product Nodes ---
    graph.add_product_node("Home Loan")
    graph.add_product_node("Personal Loan")
    graph.add_product_node("Car Loan")
    graph.add_product_node("Vehicle Loan")
    graph.add_product_node("Any")  # Universal blanket rules node

    # --- Constraint Nodes (Amounts, Scores, Ages) ---
    graph.add_constraint_node("20", node_type="Age")
    graph.add_constraint_node("23", node_type="Age")
    graph.add_constraint_node("30000", node_type="Amount")
    graph.add_constraint_node("35000", node_type="Amount")
    graph.add_constraint_node("50000", node_type="Amount")
    graph.add_constraint_node("500", node_type="Score")
    graph.add_constraint_node("650", node_type="Score")
    graph.add_constraint_node("700", node_type="Score")
    graph.add_constraint_node("5000000", node_type="Amount")
    graph.add_constraint_node("50000000", node_type="Amount")

    # --- Home Loan Rules ---
    graph.add_rule("Home Loan", "23",       relation="REQUIRES_MIN_AGE")
    graph.add_rule("Home Loan", "50000",    relation="REQUIRES_MIN_SALARY")
    graph.add_rule("Home Loan", "700",      relation="REQUIRES_MIN_CREDIT")
    graph.add_rule("Home Loan", "50000000", relation="MAX_LOAN_AMOUNT")

    # --- Personal Loan Rules ---
    graph.add_rule("Personal Loan", "20",      relation="REQUIRES_MIN_AGE")
    graph.add_rule("Personal Loan", "35000",   relation="REQUIRES_MIN_SALARY")
    graph.add_rule("Personal Loan", "700",     relation="REQUIRES_MIN_CREDIT")
    graph.add_rule("Personal Loan", "5000000", relation="MAX_LOAN_AMOUNT")

    # --- Car / Vehicle Loan Rules ---
    graph.add_rule("Car Loan", "20",    relation="REQUIRES_MIN_AGE")
    graph.add_rule("Car Loan", "30000", relation="REQUIRES_MIN_SALARY")
    graph.add_rule("Car Loan", "650",   relation="REQUIRES_MIN_CREDIT")

    graph.add_rule("Vehicle Loan", "20",    relation="REQUIRES_MIN_AGE")
    graph.add_rule("Vehicle Loan", "30000", relation="REQUIRES_MIN_SALARY")
    graph.add_rule("Vehicle Loan", "650",   relation="REQUIRES_MIN_CREDIT")

    # --- Universal Blanket Rules (Applies to all loan products) ---
    graph.add_rule("Any", "500", relation="AUTOMATIC_DISQUALIFICATION_BELOW_CREDIT")

    return graph
