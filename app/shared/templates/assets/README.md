# Assets para Templates de Email

## Isologotipo de Geonosis

Para que el email muestre correctamente el isologotipo de Geonosis, debes colocar la imagen en este directorio con el nombre exacto:

**Nombre del archivo:** `ISOLOGOTIPO-BAJADA_PRINCIPAL.png`

### Requisitos de la imagen:

- **Formato:** PNG con transparencia
- **Dimensiones recomendadas:** 200px de ancho máximo
- **Calidad:** Alta resolución para buena visualización en emails
- **Fondo:** Transparente

### Ubicación:

```
app/shared/templates/assets/ISOLOGOTIPO-BAJADA_PRINCIPAL.png
```

### Nota importante:

- Si la imagen no está presente, el sistema seguirá funcionando pero no mostrará el logo
- La imagen se convierte automáticamente a base64 para embebido en emails
- Respeta las dimensiones del manual de marca de Geonosis

### Ejemplo de uso en templates:

```html
<img
  src="data:image/png;base64,{{ISOLOGOTIPO_BASE64}}"
  alt="Geonosis"
  style="height:40px;width:auto;"
/>
```

### Imagen actual:

✅ `ISOLOGOTIPO-BAJADA_PRINCIPAL.png` - Presente y lista para usar
