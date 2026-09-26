---
type: Concepto
title: "Pausa Activa"
description: "Aplicación de escritorio que promueve pausas mediante ejercicios detectados por cámara."
tags: [python, salud, visión]
---

# Pausa Activa

Aplicación Windows que programa pausas, cubre el escritorio durante la actividad y usa MediaPipe Pose para verificar movimiento correcto durante el tiempo configurado. El ciclo se coordina con agentes y un `MessageBus` pub/sub.

La configuración vive en `config.json`; los ejercicios están en `exercises/` y las estadísticas en `data/`.

## Relaciones

- implementada_por: [[conceptos/arquitectura-multiagente]]
