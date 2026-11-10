from components.workflow.workflow_definition import EnhancedWorkflowStep, WorkflowDefinition
from domain.banking.prompts.prompt_loader import load_prompt

def create_loan_application_workflow() -> WorkflowDefinition:
    """
    Submits a new loan application atomically and emits a LOAN_APPLICATION_SUBMITTED event.
    Unchanged from original — this one was correct.
    """
    return WorkflowDefinition(
        workflow_id="loan_application_submission",
        primary_intent="submit_loan", 
        is_write_operation=True,
        name="Loan Application Submission",
        description="Submits a loan application transactionally and emits a submission event.",
        requires_auth=True,
        trigger_intents=["apply for a loan", "submit my application", "apply_loan", "submit_application", "loan_application"],
        steps=[
            EnhancedWorkflowStep(
                step_id="fetch_customer",
                action="retrieve_entity",
                name="Fetch Customer Profile",
                inputs={"resource": "customers"},
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="fetch_strict_policy",
                action="query_policy_graph",
                name="Verify Product Rules",
                inputs={},
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="submit_application_transaction",
                action="submit_loan_application",
                name="Persist Application & Emit Submission Event",
                inputs={},
                dependencies=["fetch_customer"],
            ),
            EnhancedWorkflowStep(
                step_id="confirm_submission",
                action="generate_response",
                name="Generate Application Submission Confirmation",
                inputs={
                    "system_prompt": (
                        load_prompt("submission_confirm.md")
                    )
                },
                dependencies=["submit_application_transaction"],
            ),

        ],
        input_schema={"customer_id": "str", "loan_type": "str", "amount": "float"},
    )

def create_loan_eligibility_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="loan_eligibility_check",
        primary_intent="check_eligibility",  
        name="Loan Eligibility Assessment",
        description="Checks whether a SPECIFIC person or the logged-in user meets loan eligibility requirements by evaluating their actual data against policy rules.",
        requires_auth=True,
        trigger_intents=[
            "check_eligibility", "am i eligible", "check eligibility",
            "evaluate eligibility", "eligible to apply", "qualify for",
            "can i get", "am i qualified", "do i qualify",
            "is he eligible", "is she eligible", "is the user eligible",
            "are they eligible", "eligible for", "am i eligible for a personal loan",
            "is he eligible for a home loan", "loan eligibility"
        ],

        steps=[
            EnhancedWorkflowStep(
                step_id="fetch_rules",
                action="search_documents",
                name="Fetch Loan Rules",
                inputs={"query": "loan eligibility criteria minimum requirements"},
                parallel_group="data_fetch",
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="fetch_customer",
                action="retrieve_entity",
                name="Fetch Customer Data",
                inputs={"resource": "customers"},
                parallel_group="data_fetch",
                dependencies=[],
                condition=lambda inp: bool(inp.get("id") or inp.get("target_id") or inp.get("entity_id")),
            ),
            EnhancedWorkflowStep(
                step_id="fetch_strict_policy",
                action="query_policy_graph",
                name="Fetch Strict Loan Policy Rules",
                inputs={},
                parallel_group="data_fetch",
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="decide_eligibility",
                action="generate_response",
                name="Generate Eligibility Decision",
                inputs={
                    "max_tokens": 150,
                    "system_prompt": load_prompt("eligibility_evaluation.md")
                },
                dependencies=["fetch_rules", "fetch_customer", "fetch_strict_policy"],
            ),

        ],
        input_schema={"customer_id": "str"},
    )

def create_policy_inquiry_workflow() -> WorkflowDefinition:
    """
    Fast-path pure RAG workflow for public policy inquiries, rules, criteria, and FAQs.
    Bypasses customer DB and Knowledge Graph; requires zero RBAC permissions.
    """
    return WorkflowDefinition(
        workflow_id="policy_inquiry",
        primary_intent="policy_inquiry",
        name="Loan Policy & Rules Inquiry",
        description="Answers general questions about bank policies, loan products, interest rates, guidelines, required documents, and FAQs.",
        requires_auth=False,
        trigger_intents=[
            "what are the rules", "what are the criteria", "what are the requirements",
            "loan policy", "general inquiry", "guidelines", "faq", "what documents",
            "what documents are required", "how to apply", "what is the minimum credit score",
            "what is the maximum", "tell me about", "loan products", "interest rate",
            "minimum credit score", "cibil score required"
        ],
       
        steps=[
            EnhancedWorkflowStep(
                step_id="fetch_policy_documents",
                action="search_documents",
                name="Search Policy Knowledge Base",
                inputs={},  # Uses original_query dynamically from wf_inputs
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="synthesize_policy_response",
                action="generate_response",
                name="Synthesize Policy Information",
                inputs={
                    "max_tokens": 400,
                    "system_prompt": (
                        load_prompt("policy_inquiry.md")
                    )
                },
                dependencies=["fetch_policy_documents"],
            ),
        ],
        input_schema={},
    )

def create_account_summary_workflow() -> WorkflowDefinition:
    """
    Workflow for retrieving customer profile and bank account details.
    Step 1: Fetch Customer Profile (resolves customer_id from ID or name).
    Step 2: Fetch Bank Account Details (depends on fetch_customer so customer_id cascades).
    Step 3: Generate Summary via LLM using retrieved records.
    """
    return WorkflowDefinition(
        workflow_id="account_summary",
        primary_intent="view_account",
        is_self_operation=False,
        name="Account Summary & Balance Inquiry",
        description="Retrieves a customer's personal profile and account balances.",
        requires_auth=True,
        trigger_intents=[
            "account", "balance", "profile", "account summary", "my balance", 
            "check balance", "account details", "statement", "view_account",
            "account_summary", "get_account", "customer_profile"
        ],
        steps=[
            EnhancedWorkflowStep(
                step_id="fetch_customer",
                action="retrieve_entity",
                name="Fetch Customer Profile",
                inputs={"resource": "customers"},
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="fetch_account",
                action="retrieve_entity",
                name="Fetch Bank Account Details",
                inputs={"resource": "accounts"},
                dependencies=["fetch_customer"],
            ),
            EnhancedWorkflowStep(
                step_id="summarize",
                action="generate_response",
                name="Generate Account Summary",
                inputs={
                    "system_prompt": load_prompt("account_summary.md")
                },
                dependencies=["fetch_customer", "fetch_account"],
            ),
        ],
        input_schema={"customer_id": "str"},
    )

def create_list_loan_applications_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="list_loan_applications",
        primary_intent="view_applications",     
        is_self_operation=True,
        name="List Loan Applications",
        description="Lists all loan applications submitted by a customer.",
        requires_auth=True,
        trigger_intents=[
            "status", "loan status", "application status", "check status",
            "applications", "my applications", "my loans", 
            "pending loan", "submitted", "track application",
        ],
        steps=[
            EnhancedWorkflowStep(
                step_id="fetch_all_applications",
                action="query_records",                    # ← new action, returns ALL rows
                name="Fetch All Loan Applications",
                inputs={"resource": "loan_applications", "filter_column": "customer_id"},  # filter by customer_id is auto-built from wf_inputs
                dependencies=[],
            ),
            EnhancedWorkflowStep(
                step_id="summarize_status",
                action="generate_response",
                name="Summarise Application Status",
                inputs={
                    "system_prompt": load_prompt("list_applications.md")
                },
                dependencies=["fetch_all_applications"],
            ),

        ],
        input_schema={"customer_id": "str"},
    )