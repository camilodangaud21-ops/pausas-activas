---
type: Concepto
title: "Arquitectura multiagente"
description: "Agentes independientes coordinados por publicación y suscripción de mensajes."
tags: [python, agentes, arquitectura]
---

# Arquitectura multiagente

Cada agente ejecuta una responsabilidad aislada y se comunica con otros mediante topics de `core/message_bus.py`. El scheduler determina cuándo toca una pausa, el agente visual publica pose y frames, el detector mide el ejercicio, y los agentes de pantalla y estadísticas gestionan la experiencia y el registro.

El servidor MCP de la wiki es un proceso separado; no se incorpora al ciclo de tiempo real ni a los hilos de la aplicación.

## Relaciones

- implementa: [[conceptos/pausa-activa]]
- expone_conocimiento_mediante: [[conceptos/mcp]]
