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

    def _handle_timesheet_records(self, template_content: str, context: Dict[str, Any]) -> str:
        """Maneja el renderizado de los registros de timesheet"""
        if "TIMESHEET_DATA" in context:
            timesheet_data = context.get("TIMESHEET_DATA", [])
            timesheet_html = ""
            
            for i, data in enumerate(timesheet_data):
                timesheet_html += f"""
                    <table align="center" width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#F8F9FA;border-radius:8px;border:1px solid #E9ECEF;margin:24px 0;">
                        <tbody>
                            <tr>
                                <td style="padding:20px;">
                                    <h3 style="color:#333333;font-family:'Inter Tight',-apple-system,BlinkMacSystemFont,'Segoe UI','Roboto','Oxygen','Ubuntu','Cantarell','Fira Sans','Droid Sans','Helvetica Neue',sans-serif;font-size:14px;font-weight:600;margin:0 0 12px 0;text-transform:uppercase;letter-spacing:0.5px;color:#666666;">
                                        Registro #{i + 1}
                                    </h3>
                                    <p style="font-size:15px;line-height:22px;color:#333333;font-family:'Inter Tight',-apple-system,BlinkMacSystemFont;margin:0;">
                                        <strong>Proyecto:</strong> {data.get('project_name', '')}<br />
                                        <strong>Tarea:</strong> {data.get('task_name', '')}<br />
                                        <strong>Horas:</strong> {data.get('hours', '')}<br />
                                        <strong>Fecha:</strong> {data.get('date', '')}
                                    </p>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                """
            
            template_content = template_content.replace("{{TIMESHEET_RECORDS}}", timesheet_html)

            count = len(timesheet_data)
            if count == 1:
                context["TIMESHEET_MESSAGE"] = "uno de tus registros de horas ha sido marcado"
            else:
                context["TIMESHEET_MESSAGE"] = f"{count} de tus registros de horas han sido marcados"
        
        return template_content

    def _handle_conditional_sections(self, template_content: str, context: Dict[str, Any]) -> str:
        """Maneja las secciones condicionales como el motivo de revisión"""
        show_body_section = context.get("SHOW_BODY_SECTION", "false") == "true"
        
        import re
        pattern = r'{{#if_SHOW_BODY_SECTION_true}}.*?{{/if_SHOW_BODY_SECTION_true}}'
        
        if not show_body_section:
            template_content = re.sub(pattern, '', template_content, flags=re.DOTALL)
        else:
            template_content = re.sub(r'{{#if_SHOW_BODY_SECTION_true}}|{{/if_SHOW_BODY_SECTION_true}}', '', template_content, flags=re.DOTALL)
            
        return template_content

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

        template_content = self._handle_timesheet_records(template_content, context)
        template_content = self._handle_conditional_sections(template_content, context)

        # Reemplazar todas las variables del contexto (excepto TIMESHEET_DATA que ya procesamos)
        for key, value in context.items():
            if key != "TIMESHEET_DATA":  # Skip ya que lo procesamos arriba
                placeholder = f"{{{{{key}}}}}"
                template_content = template_content.replace(placeholder, str(value))

        return template_content


# Instancia global del servicio de templates
email_template_service = EmailTemplateService()
