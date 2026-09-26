# Instrucciones de la wiki

- Empieza siempre por [`index.md`](index.md) y consulta solo las notas relevantes para la tarea.
- Conserva la separación entre la aplicación de pausas y el servidor MCP de la wiki.
- Usa `crear_concepto` para guardar aprendizajes reutilizables; no reemplaces notas existentes.
- Escribe conceptos en español y añade frontmatter YAML con `type` y `title`.
- Guarda cada relación como `- relacion: [[ruta/id-sin-extension]]` bajo `## Relaciones`.
- Usa IDs relativos exactos a `wiki/`; `query_path` solo sigue wikilinks hacia notas existentes.
- Para añadir relaciones, llama a `obsidian_add_links` con destinos explícitos; no enlaces por similitud ni inventes destinos.
- Si no hay camino almacenado, devuelve `found: false`; no completes la respuesta con conocimiento externo.
- No guardes secretos, datos personales ni información temporal en la wiki.
- Verifica los cambios con las pruebas del proyecto; las pruebas no deben necesitar cámara ni Tkinter.
- Si una decisión depende de un OKF externo que no está disponible, documéntala como pendiente y no afirmes que quedó registrada allí.
