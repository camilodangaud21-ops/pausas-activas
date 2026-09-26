"""Route wiki knowledge requests to the responsible agent."""

from wiki_mcp.knowledge_agent import KnowledgeAgent


class KnowledgeOrchestrator:
    def __init__(self, knowledge_agent: KnowledgeAgent) -> None:
        self.knowledge_agent = knowledge_agent

    def execute(self, request: dict[str, object]) -> dict[str, object]:
        action = request.get("action")
        source = request.get("source")
        target = request.get("target")
        max_hops = request.get("max_hops", 4)
        if not isinstance(action, str):
            raise ValueError("La consulta requiere action.")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("La consulta requiere source y target.")
        if not isinstance(max_hops, int):
            raise ValueError("max_hops debe ser un entero.")
        return self.knowledge_agent.answer(action, source, target, max_hops)