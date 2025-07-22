import os
import base64
from pathlib import Path
from typing import Dict, Any


class EmailTemplateService:
    """Servicio para cargar y procesar templates de email"""

    def __init__(self):
        # Obtener la ruta del directorio actual del archivo
        self.template_dir = Path(__file__).parent
        # Los assets están un nivel arriba: app/shared/templates/assets
        self.assets_dir = self.template_dir.parent / "assets"

    def load_template(self, template_name: str) -> str:
        """Carga un template de email desde el sistema de archivos"""
        template_path = self.template_dir / f"{template_name}.html"

        if not template_path.exists():
            raise FileNotFoundError(
                f"Template {template_name} no encontrado en {template_path}"
            )

        with open(template_path, "r", encoding="utf-8") as file:
            return file.read()

    def load_image_as_base64(self, image_name: str) -> str:
        """Carga una imagen como base64 para embebido en email"""
        image_path = self.assets_dir / image_name

        if not image_path.exists():
            # Si no existe la imagen, retornamos un placeholder
            return ""

        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                return encoded_string
        except Exception as e:
            # En caso de error, log y retornar placeholder
            print(f"Error cargando imagen {image_name}: {e}")
            return ""

    def render_template(self, template_name: str, **context: Any) -> str:
        """
        Renderiza un template con las variables de contexto proporcionadas.

        Args:
            template_name: Nombre del template (sin extensión .html)
            **context: Variables para reemplazar en el template

        Returns:
            Template renderizado como string
        """
        template_content = self.load_template(template_name)

        # Cargar el isologotipo como base64 si no se proporciona
        if "ISOLOGOTIPO_BASE64" not in context:
            context["ISOLOGOTIPO_BASE64"] = self.load_image_as_base64(
                "ISOLOGOTIPO_NEGRO-AZUL.png"
            )

        # Manejar condiciones especiales para mostrar/ocultar secciones
        show_body_section = context.get("SHOW_BODY_SECTION", "false") == "true"
        
        if not show_body_section:
            # Remover la sección del motivo de revisión completa
            import re
            pattern = r'{{#if_SHOW_BODY_SECTION_true}}.*?{{/if_SHOW_BODY_SECTION_true}}'
            template_content = re.sub(pattern, '', template_content, flags=re.DOTALL)
        else:
            # Remover solo las etiquetas condicionales
            template_content = template_content.replace('{{#if_SHOW_BODY_SECTION_true}}', '')
            template_content = template_content.replace('{{/if_SHOW_BODY_SECTION_true}}', '')

        # Reemplazar todas las variables del contexto
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            template_content = template_content.replace(placeholder, str(value))

        return template_content


# Instancia global del servicio de templates
email_template_service = EmailTemplateService()
