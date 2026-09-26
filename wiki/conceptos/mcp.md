---
type: Concepto
title: "MCP"
description: "Protocolo que permite a un arnés consultar recursos y ejecutar herramientas del proyecto."
tags: [mcp, wiki, herramientas]
---

# MCP

El servidor `wiki_mcp.server` expone `wiki://index` como recurso, `listar_conceptos` para enumerar Markdown y `crear_concepto` para añadir notas con frontmatter. Soporta transporte stdio para VS Code y Streamable HTTP para clientes remotos; HTTP escucha en localhost de forma predeterminada.
