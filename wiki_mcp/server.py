"""Expose the project wiki as MCP resources and tools."""

import argparse
import json
import re
import unicodedata
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from wiki_mcp.knowledge_agent import KnowledgeAgent
from wiki_mcp.orchestrator import KnowledgeOrchestrator

WIKI_ROOT = Path(__file__).resolve().parents[1] / "wiki"
CONCEPTS_ROOT = WIKI_ROOT / "conceptos"


def read_index() -> str:
    """Return the wiki entry point."""
    return (WIKI_ROOT / "index.md").read_text(encoding="utf-8")


def list_concepts() -> str:
    """List concept documents using paths relative to the wiki root."""
    concepts = sorted(
        path.relative_to(WIKI_ROOT).as_posix()
        for path in CONCEPTS_ROOT.rglob("*.md")
    )
    return "\n".join(concepts)


def _concept_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip())
    normalized = normalized.encode("ascii", "ignore").decode("ascii").lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9 _-]{0,79}", normalized):
        raise ValueError("El nombre debe usar letras, números, espacios, guiones o _.")
    return re.sub(r"[ _]+", "-", normalized).strip("-")


def obsidian_add_links(source_id: str, target_ids: list[str], relation: str) -> str:
    """Add explicit Obsidian links only to Markdown notes that exist in the wiki."""
    return KnowledgeAgent(WIKI_ROOT).add_links(source_id, target_ids, relation)


def create_concept(
    name: str,
    concept_type: str,
    content: str,
    related_ids: list[str] | None = None,
    relation: str = "relacionado_con",
) -> str:
    """Create a Markdown concept without overwriting existing wiki content."""
    title = name.strip()
    kind = concept_type.strip()
    if not title:
        raise ValueError("El nombre no puede estar vacío.")
    if not kind:
        raise ValueError("El tipo no puede estar vacío.")
    if not content.strip():
        raise ValueError("El contenido no puede estar vacío.")

    destination = CONCEPTS_ROOT / f"{_concept_slug(title)}.md"
    note_id = destination.relative_to(WIKI_ROOT).with_suffix("").as_posix()
    if related_ids:
        knowledge_agent = KnowledgeAgent(WIKI_ROOT)
        knowledge_agent.validate_relation(relation)
        knowledge_agent.validate_link_targets(related_ids)
    frontmatter = (
        "---\n"
        f"type: {json.dumps(kind, ensure_ascii=False)}\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        "tags: [wiki, generado]\n"
        "---\n\n"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x", encoding="utf-8") as concept_file:
            concept_file.write(frontmatter + content.rstrip() + "\n")
    except FileExistsError:
        return f"El concepto '{title}' ya existe; no se modificó."
    if related_ids:
        obsidian_add_links(note_id, related_ids, relation)
    return f"Creado conceptos/{destination.name}"


def build_server(host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    server = FastMCP(
        name="pausa-activa-wiki",
        instructions="Consulta el índice de la wiki antes de actuar y registra conceptos útiles.",
        host=host,
        port=port,
    )
    orchestrator = KnowledgeOrchestrator(KnowledgeAgent(WIKI_ROOT))

    @server.resource("wiki://index")
    def wiki_index() -> str:
        return read_index()

    @server.tool()
    def listar_conceptos() -> str:
        """Lista los conceptos Markdown disponibles en la wiki."""
        return list_concepts()

    @server.tool()
    def crear_concepto(
        nombre: str,
        tipo: str,
        contenido: str,
        related_ids: list[str] | None = None,
        relation: str = "relacionado_con",
    ) -> str:
        """Crea un concepto nuevo y enlaza solo los destinos existentes indicados."""
        return create_concept(nombre, tipo, contenido, related_ids, relation)

    @server.tool(name="query_path")
    def consultar_camino(
        action: str,
        source: str,
        target: str,
        max_hops: int = 4,
    ) -> dict[str, object]:
        """Busca un camino usando solo relaciones guardadas en wikilinks explícitos."""
        return orchestrator.execute(
            {"action": action, "source": source, "target": target, "max_hops": max_hops}
        )

    @server.tool()
    def obsidian_add_links(source_id: str, target_ids: list[str], relation: str) -> str:
        """Añade enlaces Obsidian a notas existentes, sin duplicar destinos."""
        return KnowledgeAgent(WIKI_ROOT).add_links(source_id, target_ids, relation)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor MCP para la wiki de Pausa Activa")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    build_server(host=args.host, port=args.port).run(transport=args.transport)


if __name__ == "__main__":
    main()