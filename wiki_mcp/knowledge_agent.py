"""Answer graph queries using only explicit links stored in the wiki."""

import re
from collections import deque
from pathlib import Path

RELATION_LINE = re.compile(
    r"^\s*-\s*(?P<relation>[\w-]+)\s*:\s*"
    r"\[\[(?P<target>[^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]\s*$"
)
RELATION_NAME = re.compile(r"[\w-]{1,60}")


class KnowledgeAgent:
    def __init__(self, wiki_root: Path) -> None:
        self.wiki_root = Path(wiki_root)

    def _documents(self) -> dict[str, str]:
        return {
            path.relative_to(self.wiki_root).with_suffix("").as_posix():
            path.read_text(encoding="utf-8")
            for path in self.wiki_root.rglob("*.md")
        }

    @staticmethod
    def _normalize_id(note_id: str) -> str:
        normalized = note_id.strip().replace("\\", "/")
        if normalized.endswith(".md"):
            normalized = normalized[:-3]
        return normalized.removeprefix("./").strip("/")

    def _relations(self, documents: dict[str, str]) -> dict[str, list[dict[str, str]]]:
        graph: dict[str, list[dict[str, str]]] = {note_id: [] for note_id in documents}
        for source_id, content in documents.items():
            for line in content.splitlines():
                match = RELATION_LINE.fullmatch(line)
                if match is None:
                    continue
                target_id = self._normalize_id(match.group("target"))
                if target_id in documents:
                    graph[source_id].append(
                        {"source": source_id, "relation": match.group("relation"), "target": target_id}
                    )
        return graph

    def validate_link_targets(self, target_ids: list[str]) -> list[str]:
        documents = self._documents()
        normalized_ids = [self._normalize_id(target_id) for target_id in target_ids]
        missing = [note_id for note_id in normalized_ids if note_id not in documents]
        if missing:
            raise ValueError(f"No existen estos destinos en la wiki: {', '.join(missing)}")
        return normalized_ids

    @staticmethod
    def validate_relation(relation: str) -> None:
        if not RELATION_NAME.fullmatch(relation):
            raise ValueError("La relación debe usar letras, números, guiones o guiones bajos.")

    def add_links(self, source_id: str, target_ids: list[str], relation: str) -> str:
        documents = self._documents()
        normalized_source = self._normalize_id(source_id)
        if normalized_source not in documents:
            raise ValueError(f"No existe la nota de origen: {normalized_source}")
        self.validate_relation(relation)

        normalized_targets = self.validate_link_targets(target_ids)
        if normalized_source in normalized_targets:
            raise ValueError("Una nota no puede enlazarse a sí misma.")

        source_path = self.wiki_root / f"{normalized_source}.md"
        content = documents[normalized_source]
        existing_targets = {
            edge["target"]
            for edge in self._relations(documents)[normalized_source]
        }
        new_links = [
            target_id for target_id in dict.fromkeys(normalized_targets)
            if target_id not in existing_targets
        ]
        if not new_links:
            return "No se añadieron enlaces: ya existían."

        updated = content.rstrip()
        if "## Relaciones" not in updated.splitlines():
            updated += "\n\n## Relaciones"
        updated += "\n" + "\n".join(
            f"- {relation}: [[{target_id}]]" for target_id in new_links
        ) + "\n"
        source_path.write_text(updated, encoding="utf-8")
        return f"Añadidos {len(new_links)} enlace(s) a {normalized_source}."

    def answer(
        self,
        action: str,
        source: str,
        target: str,
        max_hops: int = 4,
    ) -> dict[str, object]:
        if action != "query_path":
            raise ValueError("La acción debe ser 'query_path'.")
        if not source or not source.strip() or not target or not target.strip():
            raise ValueError("La consulta requiere source y target.")
        if isinstance(max_hops, bool) or not isinstance(max_hops, int) or max_hops < 0:
            raise ValueError("max_hops debe ser un entero no negativo.")

        source_id = self._normalize_id(source)
        target_id = self._normalize_id(target)
        documents = self._documents()
        graph = self._relations(documents)
        if source_id not in graph or target_id not in graph:
            return {"found": False, "source": source_id, "target": target_id}
        if source_id == target_id:
            return {
                "found": True,
                "source": source_id,
                "target": target_id,
                "hops": 0,
                "path": [source_id],
                "relationships": [],
            }

        pending = deque([(source_id, [source_id], [])])
        visited = {source_id}
        while pending:
            current_id, path, relationships = pending.popleft()
            if len(relationships) >= max_hops:
                continue
            for edge in graph[current_id]:
                next_id = edge["target"]
                if next_id in visited:
                    continue
                next_path = [*path, next_id]
                next_relationships = [*relationships, edge]
                if next_id == target_id:
                    return {
                        "found": True,
                        "source": source_id,
                        "target": target_id,
                        "hops": len(next_relationships),
                        "path": next_path,
                        "relationships": next_relationships,
                    }
                visited.add(next_id)
                pending.append((next_id, next_path, next_relationships))

        return {"found": False, "source": source_id, "target": target_id}