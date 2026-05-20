from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AgentContract:
    role_name: str
    allowed_tools: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    stop_condition: str = ""
    max_repair_loops: int = 1
    mutation_policy: str = "read_only"


CORE_AGENT_CONTRACTS: Dict[str, AgentContract] = {
    "coordinator": AgentContract(
        role_name="coordinator",
        stop_condition="workflow_completed",
        max_repair_loops=1,
    ),
    "planner": AgentContract(
        role_name="planner",
        stop_condition="route_selected",
        max_repair_loops=1,
    ),
    "retriever": AgentContract(
        role_name="retriever",
        allowed_tools=["rag_search", "vector_rag_search", "structured_lookup"],
        stop_condition="context_built",
        max_repair_loops=1,
    ),
    "tool_router": AgentContract(
        role_name="tool_router",
        allowed_tools=["mcp", "internal_tools"],
        stop_condition="tool_plan_selected",
        max_repair_loops=1,
    ),
    "domain_tutor": AgentContract(
        role_name="domain_tutor",
        stop_condition="user_answer_ready",
        max_repair_loops=1,
    ),
    "coach": AgentContract(
        role_name="coach",
        stop_condition="user_answer_ready",
        max_repair_loops=1,
    ),
    "critic": AgentContract(
        role_name="critic",
        stop_condition="output_validated",
        max_repair_loops=2,
    ),
    "executor": AgentContract(
        role_name="executor",
        stop_condition="side_effect_applied",
        max_repair_loops=0,
        mutation_policy="requires_approval",
    ),
}


def get_agent_contract(role_name: str) -> AgentContract:
    return CORE_AGENT_CONTRACTS.get(role_name, AgentContract(role_name=role_name))
