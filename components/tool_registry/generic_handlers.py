import re
import uuid
import datetime
import json
from typing import Any

from components.data_adapters.sqlite_adapter import SQLiteDataAdapter
from components.rag_engine.rag_adapter import retrieve
from contracts.common.request_context import RequestContext
from contracts.model.model_request import ModelRequest


async def generic_knowledge_search_handler(inputs: dict[str, Any]) -> dict[str, Any]:
    query = inputs.get("query") or inputs.get("original_query") or ""
    return await retrieve(query)


async def generic_resource_query_handler(inputs: dict[str, Any]) -> dict[str, Any]:
    db_path = inputs.get("db_path")
    adapter = SQLiteDataAdapter(db_path=db_path) if db_path else SQLiteDataAdapter()
    
    resource = inputs.get("resource", "entities")
    key_field = inputs.get("key_field")

    # 1. Check explicit key_field or universal platform keys
    lookup_key = (
        (inputs.get(key_field) if key_field else None)
        or inputs.get("id")
        or inputs.get("entity_id")
        or inputs.get("target_id")
        or inputs.get("name")
        or inputs.get("code")
    )

    # 2. Domain-agnostic fallback: inspect any domain ID key ending with '_id'
    if not lookup_key:
        id_keys = [
            k for k in inputs.keys()
            if k.endswith("_id") and k not in {"request_id", "session_id", "trace_id", "span_id"}
        ]
        for k in id_keys:
            if inputs.get(k):
                lookup_key = inputs[k]
                break


    if not lookup_key:
        query_text = inputs.get("query") or inputs.get("original_query") or ""
        id_match = re.search(r'\b[A-Za-z]*\d+[A-Za-z0-9_-]*\b', query_text)
        name_match = re.search(r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', query_text)
        
        if id_match:
            lookup_key = id_match.group(0)
        elif name_match:
            lookup_key = name_match.group(1)
        else:
            lookup_key = query_text

    if not lookup_key:
        return {
            "status": "failure",
            "content": f"No search key or identifier provided for resource '{resource}'.",
            "data": {},
        }

    result = await adapter.get_by_id(resource=resource, resource_id=str(lookup_key))

    if result.success and result.data and result.data.records:
        record = result.data.records[0]
        return {
            "status": "success",
            "content": f"Database Record: {record}",
            "data": record,
        }

    return {
        "status": "success",
        "content": f"No record found for '{lookup_key}' in '{resource}'.",
        "data": {},
    }

async def generic_resource_filter_handler(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Queries a table by one or more column filters, returning ALL matching rows.

    DOMAIN-AGNOSTIC: This handler knows nothing about column names or entity types.
    The caller (workflow step definition) is responsible for specifying 'filter_column'.
    The runtime value to filter on is resolved from the standard system keys: id / entity_id / target_id.
    """
    db_path = inputs.get("db_path")
    adapter = SQLiteDataAdapter(db_path=db_path) if db_path else SQLiteDataAdapter()

    resource = inputs.get("resource", "entities")

    # 1. Prefer an explicit fully-formed filters dict (e.g. passed programmatically)
    filters: dict[str, Any] = inputs.get("filters") or {}

    # 2. If no explicit filters, build one from filter_column + the standard ID keys.
    #    The WORKFLOW STEP provides filter_column (domain knowledge lives there, not here).
    #    The AGENT RUNTIME provides the value via the standard id/entity_id/target_id keys.
    if not filters:
        filter_column: str | None = inputs.get("filter_column")  # set by workflow step definition
        filter_value = (
            inputs.get("id")           # populated by agent wf_inputs
            or inputs.get("entity_id")
            or inputs.get("target_id")
        )

        if filter_column and filter_value:
            filters = {filter_column: str(filter_value)}

    if not filters:
        return {
            "status": "failure",
            "content": (
                f"No filter criteria provided to query '{resource}'. "
                "Set 'filter_column' in the workflow step inputs and ensure "
                "'id' or 'entity_id' is present in the workflow request."
            ),
            "data": {},
        }

    from contracts.adapters.data_adapter_contract import DataQuery
    data_query = DataQuery(resource=resource, filters=filters, limit=20)
    result = await adapter.query(data_query)

    if result.success and result.data and result.data.records:
        records = result.data.records
        lines = [
            f"  [{i+1}] " + ", ".join(f"{k}: {v}" for k, v in rec.items())
            for i, rec in enumerate(records)
        ]
        content = f"Found {len(records)} record(s) in '{resource}':\n" + "\n".join(lines)
        return {
            "status": "success",
            "content": content,
            "data": {"records": records, "count": len(records)},
        }

    return {
        "status": "success",
        "content": f"No records found in '{resource}' for filters: {filters}.",
        "data": {"records": [], "count": 0},
    }


def create_knowledge_graph_handler(graph_adapter):
    """
    Domain-agnostic Knowledge Graph handler.
    Supplies exact graph constraints if present; otherwise allows RAG/SLM to handle gracefully.
    """
    async def handler(inputs: dict[str, Any]) -> dict[str, Any]:
        query = inputs.get("query") or inputs.get("original_query") or ""
        intent = inputs.get("intent") or ""
        history = inputs.get("history") or ""

        # 1. Direct query matching
        result = graph_adapter.execute(query)

        # 2. Context resolution fallback
        if result.startswith("Error") and intent:
            result = graph_adapter.execute(intent.replace("_", " "))
        if result.startswith("Error") and history:
            result = graph_adapter.execute(history)


        # 3. Graceful fallback without crashing workflow
        if result.startswith("Error"):
            return {
                "status": "success",
                "content": "No specific deterministic graph constraints matched. Rely on retrieved documentation and records."
            }

        return {
            "status": "success",
            "content": f"Deterministic Graph Constraints:\n{result}"
        }
    return handler


def create_response_generator_handler(model_gateway, model_name: str):
    """
    Domain-agnostic response synthesizer.
    Follows the Task-Contract Pattern: executes the exact prompt contract
    provided by the workflow step, with a neutral assistant fallback for ad-hoc plans.
    """
    async def handler(inputs: dict[str, Any]) -> dict[str, Any]:
        context = inputs.get("context", "").strip()
        query = inputs.get("original_query", "").strip()
        history = inputs.get("history", "").strip()

        if not context and not history:
            return {
                "status": "success",
                "content": "I could not find relevant information to answer your request.",
            }

        # 1. Transaction receipts bypass LLM generation entirely
        if "Transaction committed successfully!" in context:
            for line in context.splitlines():
                if "Transaction committed successfully!" in line:
                    clean_receipt = line.split("]:", 1)[-1].strip() if "]:" in line else line.strip()
                    return {
                        "status": "success",
                        "content": clean_receipt,
                    }

        # 2. Neutral domain-agnostic fallback for ad-hoc / unprompted queries
        DEFAULT_PROMPT = (
            "You are a helpful, professional assistant.\n"
            "Answer the user's request directly, accurately, and concisely using ONLY the provided context and records.\n"
            "If the user asks for a specific value or fact, state it directly in clear, natural language.\n"
            "Do not include unsolicited verdicts, approval statements, or internal tool headers."
        )

        # The workflow step supplies its own specific prompt contract
        system_prompt = inputs.get("system_prompt") or DEFAULT_PROMPT
        max_tokens = inputs.get("max_tokens", 800)
        prompt_parts = []
        if context:
            prompt_parts.append(f"PRIMARY SOURCE OF TRUTH (Retrieved Records & Data):\n{context}")
        if history:
            prompt_parts.append(
                f"BACKGROUND DIALOGUE REFERENCE (Use ONLY to resolve pronouns like 'it', 'he', or 'that loan'. "
                f"Do NOT answer from this history if the current query is an independent question):\n{history}"
            )
        prompt_parts.append(f"CURRENT USER REQUEST: {query}\n\nAnswer:")

        prompt = "\n\n".join(prompt_parts)

        request = ModelRequest(
            request_context=RequestContext(
                request_id="response-gen",
                correlation_id="response-gen",
                session_id="response-gen",
                user_id="system",
                tenant_id="system",
            ),
            system_prompt=system_prompt,
            prompt=prompt,
            model=model_name,
            temperature=0.0,
            max_tokens=max_tokens,
        )

        response = await model_gateway.generate(request)

        # Truncate synthetic few-shot loops: the 3B SLM sometimes generates
        # repeated "User Request: ... Answer: ..." pairs after the real answer.
        raw = response.content.strip()
        if "User Request:" in raw:
            raw = raw.split("User Request:")[0].strip()

        # Stop repeating paragraph/bullet loops
        paragraphs = raw.split("\n\n")
        seen_paragraphs = set()
        clean_paragraphs = []
        for p in paragraphs:
            norm_p = p.strip()
            if norm_p and norm_p in seen_paragraphs:
                break
            if norm_p:
                seen_paragraphs.add(norm_p)
                clean_paragraphs.append(p)
        raw = "\n\n".join(clean_paragraphs)

        return {
            "status": "success",
            "content": raw,
        }
    return handler


async def generic_resource_create_handler(inputs: dict[str, Any]) -> dict[str, Any]:
    """Domain-agnostic single record creation."""
    db_path = inputs.get("db_path")
    adapter = SQLiteDataAdapter(db_path=db_path) if db_path else SQLiteDataAdapter()
    resource = inputs.get("resource", "entities")
    data = inputs.get("data", {})

    result = await adapter.insert_record(resource=resource, data=data)
    if result.success:
        return {"status": "success", "content": f"Record created in '{resource}'.", "data": result.data}
    return {"status": "failure", "content": f"Failed to create record in '{resource}': {result.data.get('error')}", "data": result.data}


async def generic_transaction_handler(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Domain-agnostic atomic transaction handler.
    Executes multiple write operations in a single atomic transaction.
    """
    db_path = inputs.get("db_path")
    adapter = SQLiteDataAdapter(db_path=db_path) if db_path else SQLiteDataAdapter()
    operations = inputs.get("operations", [])

    if not operations:
        return {
            "status": "failure",
            "content": "No transactional operations supplied to execute.",
            "data": {},
        }

    result = await adapter.execute_transaction(operations=operations)
    if result.success:
        op_count = len(operations)
        return {
            "status": "success",
            "content": f"Transaction committed successfully! Total operations executed: {op_count}.",
            "data": result.data,
        }
    return {
        "status": "failure",
        "content": f"Transaction aborted and rolled back: {result.data.get('error')}",
        "data": result.data,
    }

