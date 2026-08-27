# Prompt para Claude — Generar PDF de la solución técnica

Pegá este prompt en Claude (claude.ai) junto con el contenido del archivo `GEOTIMESHIFT_EQUIPOS_SOLUCION.md`:

---

## PROMPT

Sos un arquitecto de software senior. Tenés que convertir la siguiente documentación técnica en un documento PDF profesional en español, bien estructurado y visual, pensado para presentar a un equipo de desarrollo y a stakeholders técnicos.

El documento debe:

**Estructura:**
- Portada con título, subtítulo "Propuesta de arquitectura técnica", y fecha actual
- Índice de contenidos
- Sección 1: Contexto y problema actual (con tabla de limitaciones)
- Sección 2: Solución propuesta (dividida en los 3 componentes)
- Sección 3: Flujo completo end-to-end (con diagrama de texto o ASCII)
- Sección 4: Tabla de roles y permisos
- Sección 5: Consideraciones de seguridad
- Sección 6: Orden de implementación (como checklist numerado)
- Sección 7: Archivos a modificar (como árbol de directorios)

**Estilo visual:**
- Profesional, limpio, con colores corporativos suaves (azul/gris)
- Tablas bien formateadas con headers destacados
- Bloques de código con fondo diferenciado (gris claro)
- Íconos o bullets visuales para listas de pasos
- Tipografía: títulos en negrita, código en monospace
- Cada sección en su propia página si el contenido lo justifica
- Notas de advertencia (como la sección de seguridad) con recuadro destacado en amarillo/naranja suave

**Formato de entrega:**
Generá el documento como HTML bien formateado y con estilos CSS inline (para que pueda imprimirse como PDF desde el browser con Ctrl+P → Guardar como PDF), o directamente como PDF si es posible.

El documento NO debe verse como una página web genérica. Debe verse como un documento técnico profesional, similar a un RFC o una propuesta de arquitectura empresarial.

---

[PEGÁ AQUÍ EL CONTENIDO DEL ARCHIVO GEOTIMESHIFT_EQUIPOS_SOLUCION.md]
