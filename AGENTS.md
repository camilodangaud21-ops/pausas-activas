---
type: Proyecto
title: Pausa Activa - sistema multiagente de pausas activas con estimación de pose
description: Sistema de escritorio en Python que bloquea la pantalla periódicamente y usa MediaPipe Pose (vía webcam) para verificar que el usuario complete un ejercicio antes de desbloquear. Arquitectura multiagente sobre un MessageBus pub/sub.
status: desarrollo
tags: [python, tkinter, mediapipe, opencv, multiagente, pausas-activas]
timestamp: 2026-09-26
creator: "Camilo"
---

# AGENTS.md

## Propósito

Este repositorio contiene un sistema de escritorio agéntico: varios agentes
autónomos (cámara/pose, temporizador, detector de ejercicio, estadísticas,
bandeja del sistema, bloqueo de pantalla) que se coordinan exclusivamente a
través de un `MessageBus` publicar/suscribir, sin llamarse entre sí.

## Reglas de trabajo

1. El `MessageBus` (`core/message_bus.py`) es la única vía de comunicación
   entre agentes. Ningún agente debe importar o llamar directamente a otro
   agente; toda interacción va por `bus.publish(...)` / `bus.subscribe(...)`.
2. Cada agente nuevo debe heredar de `agents/base_agent.py` (`BaseAgent`) y
   correr en su propio hilo, salvo que necesite el hilo principal (como
   `LockScreenAgent`, que usa Tkinter) — en ese caso debe replicar a mano el
   mismo patrón de suscripción/poll, no bloquear el `mainloop`.
3. Todo topic nuevo del bus (ej. `"pause_due"`, `"exercise_complete"`) debe
   quedar documentado en el docstring del agente que lo publica/escucha y en
   la tabla de agentes de `README.md`.
4. El criterio de desbloqueo (segundos de movimiento activo acumulado, hoy
   60s) no debe debilitarse sin justificarlo explícitamente en el commit —
   es la garantía central de que el ejercicio se hizo de verdad.
5. Cualquier atajo de emergencia o bypass del bloqueo (ej. el combo
   Ctrl+Shift+Esc) debe quedar siempre registrado vía `logging` y en
   `StatsAgent`/`data/stats.json`; nunca debe ser silencioso.
6. No añadas dependencias externas sin actualizar `requirements.txt` (con
   versión fijada) y `README.md`. Verifica compatibilidad con la versión de
   Python del proyecto antes de fijar una versión.
7. Los archivos generados en tiempo de ejecución (modelo `.task` de
   MediaPipe, logs, `stats.json`, `postpones.json`) van en `models/` o
   `data/`, nunca se commitean — deben estar en `.gitignore` (una entrada
   por línea, no todas juntas en una sola línea).
8. Cambios de comportamiento en un ejercicio (`exercises/*.py`) o en la
   lógica de posponer/calibrar deben incluir una prueba enfocada en
   `test/`, usando landmarks sintéticos (no requieren cámara real).
9. Antes de tocar un agente existente, revisa su docstring y el de los
   agentes con los que se comunica (mismos topics) para no duplicar
   responsabilidades ni romper el contrato de mensajes.
10. `main.py` es el único lugar donde se instancian y arrancan los agentes;
    no arranques agentes desde otros módulos.
11. Toda funcionalidad nueva debe degradarse con elegancia si falta una
    dependencia opcional (ej. `pystray` para `TrayAgent`, `opencv`/`mediapipe`
    para `VisionAgent`): loguear y seguir, nunca tumbar el programa completo.

## Estructura

| Ruta         | Contenido                                                                                                                        |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `core/`      | Bus de mensajes, `Message`, geometría, logging, almacén de estadísticas.                                                         |
| `agents/`    | Los agentes: configuración, temporizador, visión, detector de ejercicio, estadísticas, bandeja del sistema, bloqueo de pantalla. |
| `exercises/` | Detectores de ejercicio: funciones puras sobre landmarks, sin dependencias de cámara.                                            |
| `wiki_mcp/`  | Servidor MCP, orquestador y consultas basadas en relaciones verificadas de la wiki.                                              |
| `wiki/`      | Conocimiento Markdown; las aristas son wikilinks explícitos a notas existentes.                                                  |
| `test/`      | Pruebas con pytest; no requieren cámara ni MediaPipe (usan landmarks sintéticos).                                                |
| `scripts/`   | Utilidades independientes del programa principal (ej. autoarranque en Windows).                                                  |
| `data/`      | Estado en tiempo de ejecución: logs, `stats.json`, `postpones.json`. No se commitea.                                             |
| `models/`    | Modelo `.task` de MediaPipe, descargado en el primer arranque. No se commitea.                                                   |

## Flujo obligatorio

`README.md` → `AGENTS.md` → agente o módulo relevante → topic del bus a crear
o modificar → prueba enfocada en `test/` → commit.

## Flujo de una tarea

1. Revisa `core/message_bus.py` y el agente relacionado antes de tocar el
   modelo de mensajes o agregar un topic nuevo.
2. Para introducir un comportamiento nuevo, comunícalo por el bus
   (`bus.publish(...)` / `bus.subscribe([...])`); no llames métodos de otro
   agente directamente.
3. Si la capacidad nueva debe correr de forma autónoma, créala como un
   agente en `agents/`, heredando de `BaseAgent` (o replicando su patrón si
   necesita el hilo principal, como `LockScreenAgent`).
4. Antes de dar por terminado un cambio, ejecuta:
   `python -m pytest test -v` y
   `python -m compileall -q agents core exercises test scripts main.py`.
