---
type: Proyecto
title: "Pausa Activa"
description: "Pausas activas asistidas por detección de pose y conocimiento consultable vía MCP."
status: desarrollo
tags: [python, mcp, agentes, salud]
timestamp: 2026-09-26
creator: "Gerardo Esquivia Zapata"
---

# Pausa Activa

## Propósito

Ayudar a programadores a interrumpir el trabajo sedentario con ejercicios detectados en tiempo real por cámara.

## Meta

Completar pausas configurables de movimiento, conservar estadísticas y permitir que distintos arneses consulten y amplíen el conocimiento del proyecto mediante MCP.

## Metodología

La aplicación usa agentes desacoplados con comunicación pub/sub. Los ejercicios son lógica aislada y se prueban con landmarks sintéticos. La wiki Markdown se sirve en un proceso MCP separado para evitar acoplarla al ciclo de cámara/UI.

## Estrategia

- Usar `MessageBus` para coordinar los agentes de la aplicación.
- Mantener `wiki/index.md` como entrada y los conceptos bajo `wiki/conceptos/`.
- Conectar VS Code por stdio y permitir Streamable HTTP solo en localhost por defecto.
- Verificar las operaciones MCP y la aplicación con pruebas automatizadas.

## Archivos y Formas Creadas

- `agents/`, `core/`, `exercises/`: lógica multiagente de pausas activas.
- `wiki_mcp/server.py`: recurso de índice y herramientas de listar/crear conceptos.
- `wiki/`: índice, instrucciones, tareas y conceptos con frontmatter.
- `.vscode/mcp.json`: configuración del servidor para VS Code.

## Resultados

El servidor MCP local está implementado y cuenta con pruebas unitarias. La inscripción en un OKF externo queda pendiente: no se encontró el repositorio del OKF en este entorno.

## Referencias

- [[MCP]] en `wiki/conceptos/mcp.md`.
- [[Arquitectura multiagente]] en `wiki/conceptos/arquitectura-multiagente.md`.
- [Cerebro MCP](https://gerardoesquivia.com/cerebro-mcp/).
- [Open Knowledge Format](https://gerardoesquivia.com/open-knowledge-format/).
