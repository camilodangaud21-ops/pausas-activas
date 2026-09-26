"""Expose the project wiki as MCP resources and tools."""

import argparse
import json
import re
import unicodedata
from pathlib import Path

from mcp.server.fastmcp import FastMCP

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


def create_concept(name: str, concept_type: str, content: str) -> str:
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
    return f"Creado conceptos/{destination.name}"


def build_server(host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    server = FastMCP(
        name="pausa-activa-wiki",
        instructions="Consulta el índice de la wiki antes de actuar y registra conceptos útiles.",
        host=host,
        port=port,
    )

    @server.resource("wiki://index")
    def wiki_index() -> str:
        return read_index()

    @server.tool()
    def listar_conceptos() -> str:
        """Lista los conceptos Markdown disponibles en la wiki."""
        return list_concepts()

    @server.tool()
    def crear_concepto(nombre: str, tipo: str, contenido: str) -> str:
        """Crea un concepto Markdown nuevo, sin reemplazar uno existente."""
        return create_concept(nombre, tipo, contenido)

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