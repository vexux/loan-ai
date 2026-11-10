from contracts.common.enums import ApprovalStatus, RiskLevel
from contracts.common.request_context import RequestContext
from contracts.policy.policy_contract import PolicyAction, PolicyRequest
from components.policy.policy_engine import RuleBasedPolicyEngine


def test_policy_allow_action():
    engine = RuleBasedPolicyEngine(allowed_actions=["search_documents", "retrieve_entity"])
    context = RequestContext(request_id="1", session_id="1", correlation_id="1", user_id="u1", tenant_id="t1")
    
    req = PolicyRequest(context=context, action="search_documents", component_name="ToolRegistry")
    res = engine.evaluate(req)

    assert res.success is True
    assert res.data.allowed is True
    assert res.data.action == PolicyAction.ALLOW


def test_policy_deny_unauthorized_action():
    engine = RuleBasedPolicyEngine(allowed_actions=["search_documents"])
    context = RequestContext(request_id="1", session_id="1", correlation_id="1", user_id="u1", tenant_id="t1")
    
    req = PolicyRequest(context=context, action="drop_database", component_name="ToolRegistry")
    res = engine.evaluate(req)

    assert res.success is True
    assert res.data.allowed is False
    assert res.data.action == PolicyAction.DENY
    assert len(res.data.reasons) > 0