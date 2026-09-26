---
type: Proyecto
title: "Pausa Activa — Sistema multiagente y wiki MCP"
description: "Programa pausas activas con detección de pose y expone el conocimiento del proyecto mediante MCP."
status: desarrollo
tags: [python, mcp, agente, wiki]
timestamp: 2026-09-26
creator: "Gerardo Esquivia Zapata"
---

# Reglas del proyecto

## Convenciones obligatorias

- Mantén los agentes desacoplados: comunícalos mediante `core/message_bus.py`.
- Mantén el servidor de la wiki independiente de la aplicación de pausas.
- Escribe archivos de texto en UTF-8 y declara cada dependencia en `requirements.txt`.
- No sobrescribas conceptos existentes al usar `crear_concepto`.
- Cada documento de `wiki/conceptos/` debe incluir frontmatter YAML con `type` y `title`.
- Ejecuta las pruebas sin requerir cámara, MediaPipe ni interfaz gráfica.

## Estructura

| Ruta                             | Contenido                                          |
| -------------------------------- | -------------------------------------------------- |
| `agents/`, `core/`, `exercises/` | Agentes, bus y lógica de ejercicios                |
| `wiki_mcp/`                      | Servidor MCP de la wiki                            |
| `wiki/`                          | Índice, instrucciones, tareas y conceptos Markdown |
| `test/`                          | Pruebas unitarias                                  |
| `scripts/`                       | Automatización de arranque de Windows              |
| `data/`                          | Configuración mutable y estadísticas               |
| `📋 Proyectos/Pausa Activa.md`   | Nota local de registro del proyecto                |
| `📋 Proyectos/index.md`          | Índice de proyectos con propósito y meta           |
| `INDICE_DE_SKILLS.md`            | Índice local de habilidades reutilizables          |

## Scripts y comandos

| Script/comando      | Ejecución                                               | Resultado                                     |
| ------------------- | ------------------------------------------------------- | --------------------------------------------- |
| Aplicación          | `python main.py`                                        | Inicia los agentes de pausas activas          |
| Servidor MCP stdio  | `python -m wiki_mcp.server`                             | Expone el índice y las herramientas MCP       |
| Servidor MCP HTTP   | `python -m wiki_mcp.server --transport streamable-http` | Expone MCP en `127.0.0.1:8765/mcp`            |
| Pruebas             | `python -m pytest test/`                                | Ejecuta pruebas sin cámara ni UI              |
| Arranque de Windows | `python scripts/add_to_startup.py`                      | Registra la aplicación en el inicio de sesión |

## Datos de referencia

- El intervalo de pausa, la cámara y el tiempo activo requerido se configuran en `config.json`.
- Las estadísticas se guardan en `data/stats.json` y las posposiciones en `data/postpones.json`.
- El índice de la wiki es `wiki/index.md`; los conceptos viven en `wiki/conceptos/`.
- La dependencia MCP está acotada a la serie 1.x en `requirements.txt`.

## Conocimiento relacionado

- Nota del proyecto: [[Pausa Activa]] en `📋 Proyectos/Pausa Activa.md`.
- Índice local: [`📋 Proyectos/index.md`](📋%20Proyectos/index.md).
- Habilidades: `INDICE_DE_SKILLS.md`.
- Índice de proyectos OKF: https://gerardoesquivia.com/cerebro-mcp/
- Formato OKF: https://gerardoesquivia.com/open-knowledge-format/
