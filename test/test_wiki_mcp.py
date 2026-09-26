import pytest

from wiki_mcp.knowledge_agent import KnowledgeAgent
from wiki_mcp.orchestrator import KnowledgeOrchestrator
import wiki_mcp.server as wiki_server


def use_temporary_wiki(tmp_path, monkeypatch):
    wiki_root = tmp_path / "wiki"
    concepts_root = wiki_root / "conceptos"
    concepts_root.mkdir(parents=True)
    (wiki_root / "index.md").write_text("# Wiki de prueba\n", encoding="utf-8")
    monkeypatch.setattr(wiki_server, "WIKI_ROOT", wiki_root)
    monkeypatch.setattr(wiki_server, "CONCEPTS_ROOT", concepts_root)
    return wiki_root, concepts_root


def test_read_index_returns_wiki_entrypoint(tmp_path, monkeypatch):
    use_temporary_wiki(tmp_path, monkeypatch)

    assert wiki_server.read_index() == "# Wiki de prueba\n"


def test_list_concepts_returns_sorted_relative_paths(tmp_path, monkeypatch):
    _, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    (concepts_root / "zeta.md").write_text("# Zeta\n", encoding="utf-8")
    nested = concepts_root / "subtema"
    nested.mkdir()
    (nested / "alfa.md").write_text("# Alfa\n", encoding="utf-8")

    assert wiki_server.list_concepts() == "conceptos/subtema/alfa.md\nconceptos/zeta.md"


def test_create_concept_writes_frontmatter_and_content(tmp_path, monkeypatch):
    _, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)

    result = wiki_server.create_concept("Pausas activas", "Concepto", "Moverse ayuda.")

    created = concepts_root / "pausas-activas.md"
    assert result == "Creado conceptos/pausas-activas.md"
    assert 'type: "Concepto"' in created.read_text(encoding="utf-8")
    assert 'title: "Pausas activas"' in created.read_text(encoding="utf-8")
    assert created.read_text(encoding="utf-8").endswith("Moverse ayuda.\n")


def test_create_concept_rejects_path_components(tmp_path, monkeypatch):
    use_temporary_wiki(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="nombre"):
        wiki_server.create_concept("../fuera", "Concepto", "Contenido")


def test_create_concept_does_not_overwrite_existing_file(tmp_path, monkeypatch):
    _, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    created = concepts_root / "pausas-activas.md"
    created.write_text("Contenido original\n", encoding="utf-8")

    result = wiki_server.create_concept("Pausas activas", "Concepto", "Contenido nuevo")

    assert "ya existe" in result
    assert created.read_text(encoding="utf-8") == "Contenido original\n"


def test_create_concept_adds_links_only_to_verified_related_notes(tmp_path, monkeypatch):
    wiki_root, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    (concepts_root / "existente.md").write_text("# Existente\n", encoding="utf-8")

    result = wiki_server.create_concept(
        "Nuevo concepto",
        "Concepto",
        "Nota de prueba.",
        related_ids=["conceptos/existente"],
        relation="documenta",
    )

    created = concepts_root / "nuevo-concepto.md"
    assert result == "Creado conceptos/nuevo-concepto.md"
    assert "- documenta: [[conceptos/existente]]" in created.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="No existen"):
        wiki_server.create_concept(
            "No debe crearse",
            "Concepto",
            "Nota de prueba.",
            related_ids=["conceptos/inexistente"],
        )
    assert not (concepts_root / "no-debe-crearse.md").exists()


def test_query_path_returns_only_explicit_relationships(tmp_path, monkeypatch):
    wiki_root, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    first = concepts_root / "primero.md"
    second = concepts_root / "segundo.md"
    third = concepts_root / "tercero.md"
    first.write_text("# Primero\n\n## Relaciones\n- implementa: [[conceptos/segundo]]\n", encoding="utf-8")
    second.write_text("# Segundo\n\n## Relaciones\n- usa: [[conceptos/tercero]]\n", encoding="utf-8")
    third.write_text("# Tercero\n", encoding="utf-8")
    orchestrator = KnowledgeOrchestrator(KnowledgeAgent(wiki_root))

    result = orchestrator.execute(
        {"action": "query_path", "source": "conceptos/primero", "target": "conceptos/tercero"}
    )

    assert result == {
        "found": True,
        "source": "conceptos/primero",
        "target": "conceptos/tercero",
        "hops": 2,
        "path": ["conceptos/primero", "conceptos/segundo", "conceptos/tercero"],
        "relationships": [
            {"source": "conceptos/primero", "relation": "implementa", "target": "conceptos/segundo"},
            {"source": "conceptos/segundo", "relation": "usa", "target": "conceptos/tercero"},
        ],
    }


def test_query_path_returns_false_without_a_stored_connection(tmp_path, monkeypatch):
    wiki_root, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    (concepts_root / "origen.md").write_text("# Origen\n", encoding="utf-8")
    (concepts_root / "destino.md").write_text("# Destino\n", encoding="utf-8")
    agent = KnowledgeAgent(wiki_root)

    assert agent.answer("query_path", "conceptos/origen", "conceptos/destino") == {
        "found": False,
        "source": "conceptos/origen",
        "target": "conceptos/destino",
    }


def test_query_path_enforces_max_hops_and_required_endpoints(tmp_path, monkeypatch):
    wiki_root, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    (concepts_root / "origen.md").write_text(
        "# Origen\n\n## Relaciones\n- va_a: [[conceptos/destino]]\n", encoding="utf-8"
    )
    (concepts_root / "destino.md").write_text("# Destino\n", encoding="utf-8")
    agent = KnowledgeAgent(wiki_root)

    assert agent.answer("query_path", "conceptos/origen", "conceptos/destino", 0)["found"] is False
    with pytest.raises(ValueError, match="source y target"):
        agent.answer("query_path", "", "conceptos/destino")


def test_query_path_returns_zero_hop_for_same_existing_note(tmp_path, monkeypatch):
    wiki_root, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    (concepts_root / "misma.md").write_text("# Misma nota\n", encoding="utf-8")
    agent = KnowledgeAgent(wiki_root)

    assert agent.answer("query_path", "conceptos/misma", "conceptos/misma") == {
        "found": True,
        "source": "conceptos/misma",
        "target": "conceptos/misma",
        "hops": 0,
        "path": ["conceptos/misma"],
        "relationships": [],
    }


def test_obsidian_add_links_validates_targets_and_deduplicates(tmp_path, monkeypatch):
    wiki_root, concepts_root = use_temporary_wiki(tmp_path, monkeypatch)
    source = concepts_root / "origen.md"
    target = concepts_root / "destino.md"
    source.write_text("# Origen\n", encoding="utf-8")
    target.write_text("# Destino\n", encoding="utf-8")
    agent = KnowledgeAgent(wiki_root)

    assert agent.add_links("conceptos/origen", ["conceptos/destino"], "relaciona")
    assert agent.add_links("conceptos/origen", ["conceptos/destino"], "relaciona") == (
        "No se añadieron enlaces: ya existían."
    )
    with pytest.raises(ValueError, match="No existen"):
        agent.add_links("conceptos/origen", ["conceptos/no-existe"], "relaciona")