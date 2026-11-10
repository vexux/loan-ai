import re
import uuid
import datetime
import json
from typing import Any
from components.data_adapters.sqlite_adapter import SQLiteDataAdapter


async def banking_loan_application_handler(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Banking domain-specific transactional handler for loan application submissions.
    Persists application record and emits audit event in an atomic transaction.
    """
    db_path = inputs.get("db_path")
    adapter = SQLiteDataAdapter(db_path=db_path) if db_path else SQLiteDataAdapter()
    
    query = inputs.get("original_query", "")
    customer_id = inputs.get("customer_id") or inputs.get("id") or inputs.get("entity_id") or "C001"
    
    # Identify loan type from context
    loan_type = "Home Loan"
    if "car" in query.lower() or "vehicle" in query.lower():
        loan_type = "Car Loan"
    elif "personal" in query.lower():
        loan_type = "Personal Loan"

    # Identify requested amount from context
    amount = 1000000.0
    amt_match = re.search(r'(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|cr|crore)?', query, re.IGNORECASE)
    if amt_match:
        try:
            val = float(amt_match.group(1).replace(',', ''))
            if 'lakh' in query.lower() or 'lac' in query.lower():
                val = val * 100000
            elif 'cr' in query.lower() or 'crore' in query.lower():
                val = val * 10000000
            if val > 10000:
                amount = val
        except Exception:
            pass

    app_id = f"APP-{uuid.uuid4().hex[:6].upper()}"
    event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trace_id = inputs.get("trace_id", f"TRC-{uuid.uuid4().hex[:8]}")

    operations = [
        {
            "resource": "loan_applications",
            "data": {
                "application_id": app_id,
                "customer_id": customer_id,
                "loan_type": loan_type,
                "loan_amount": amount,
                "tenure_months": 240 if "home" in loan_type.lower() else 60,
                "purpose": f"{loan_type} requested via AI conversational assistant",
                "status": "SUBMITTED",
                "applied_on": now_str,
                "idempotency_key": f"IDEMP-{app_id}"
            }
        },
        {
            "resource": "application_events",
            "data": {
                "event_id": event_id,
                "event_type": "LOAN_APPLICATION_SUBMITTED",
                "application_id": app_id,
                "customer_id": customer_id,
                "loan_type": loan_type,
                "payload_json": json.dumps({"loan_amount": amount, "status": "SUBMITTED", "channel": "CONVERSATIONAL_AGENT"}),
                "created_at": now_str,
                "trace_id": trace_id
            }
        }
    ]

    result = await adapter.execute_transaction(operations=operations)
    if result.success:
        return {
            "status": "success",
            "content": f"Transaction committed successfully! Application ID: {app_id} | Status: SUBMITTED | Event Emitted: LOAN_APPLICATION_SUBMITTED (Event ID: {event_id})",
            "data": result.data
        }
    return {
        "status": "failure",
        "content": f"Transaction aborted and rolled back: {result.data.get('error')}",
        "data": result.data
    }
