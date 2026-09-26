import pytest

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