from app.users.domain.repositories import EmployeeGateway, UserRepository
from app.users.domain.models import User
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from typing import Optional, Dict, Any


class SyncUsersUseCase:
    def __init__(
        self, employee_gateway: EmployeeGateway, user_repository: UserRepository
    ):
        self.employee_gateway = employee_gateway
        self.user_repository = user_repository

    def execute(self):
        """
        Sincroniza cambios de todos los empleados desde Odoo.
        - Para empleados CON user_id: actualiza email, nombre y roles si han cambiado
        - Para empleados SIN user_id: actualiza solo email y nombre, mantiene roles actuales
        - Solo procesa empleados que ya existen en la base de datos local
        """
        # Verificar que el gateway sea OdooEmployeeGateway para acceder a métodos específicos
        if not isinstance(self.employee_gateway, OdooEmployeeGateway):
            raise ValueError(
                "Gateway debe ser OdooEmployeeGateway para sincronización con roles"
            )

        # 1. Obtener todos los empleados con datos de usuario desde Odoo
        odoo_employees_data = self.employee_gateway.get_all_employees_with_user_data()

        if not odoo_employees_data:
            return {
                "created": 0,
                "updated": 0,
                "total_processed": 0,
                "errors": [],
            }

        # 2. Procesar cada empleado
        updated_count = 0
        total_processed = 0
        errors = []

        for employee_data in odoo_employees_data:
            total_processed += 1

            try:
                result = self._sync_single_employee(employee_data)
                if result["success"] and result["user_updated"]:
                    updated_count += 1
                elif not result["success"]:
                    errors.append(
                        {
                            "employee_id": employee_data.get("id"),
                            "message": result["message"],
                        }
                    )
            except Exception as e:
                errors.append(
                    {
                        "employee_id": employee_data.get("id"),
                        "message": f"Error inesperado: {str(e)}",
                    }
                )

        print(f"✅ Sincronización completada:")
        print(f"   🔄 {updated_count} usuarios actualizados")
        print(f"   👥 {total_processed} empleados procesados desde Odoo")
        if errors:
            print(f"   ⚠️ {len(errors)} errores encontrados")

        return {
            "created": 0,  # No creamos usuarios nuevos, solo actualizamos existentes
            "updated": updated_count,
            "total_processed": total_processed,
            "errors": errors,
        }

    def _sync_single_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza un empleado específico con la misma lógica que SyncSingleUserChangesUseCase.

        Args:
            employee_data: Datos del empleado desde Odoo

        Returns:
            Dict con información del resultado de la sincronización
        """
        employee_id = employee_data.get("id")
        has_user = employee_data.get("has_user", False)
        user_id = employee_data.get("user_id")
        odoo_name = employee_data.get("name", "")
        odoo_email = employee_data.get("email", "")
        odoo_roles = employee_data.get("roles", [])

        # Validar que employee_id sea un entero válido
        if not isinstance(employee_id, int):
            return {
                "success": False,
                "message": f"ID de empleado inválido: {employee_id}",
                "user_updated": False,
            }

        # Buscar el usuario en la base de datos local
        if has_user and user_id:
            # Empleado CON user_id: buscar por ID y sincronizar nombre, email y roles
            local_employee = self.user_repository.get_by_id(employee_id)
            if not local_employee:
                return {
                    "success": False,
                    "message": f"Usuario con id {employee_id} (asociado al empleado {employee_id}) no encontrado en la base de datos local",
                    "user_updated": False,
                }

            # Comparar cambios incluyendo roles
            has_changes = (
                local_employee.email != odoo_email
                or local_employee.full_name != odoo_name
                or local_employee.roles != odoo_roles
            )

        else:
            # Empleado SIN user_id: buscar por email y sincronizar solo nombre y email
            local_employee = self.user_repository.get_by_email(odoo_email)
            if not local_employee:
                return {
                    "success": False,
                    "message": f"Usuario con email {odoo_email} (empleado {employee_id}) no encontrado en la base de datos local",
                    "user_updated": False,
                }

            # Comparar cambios SIN incluir roles
            has_changes = (
                local_employee.email != odoo_email
                or local_employee.full_name != odoo_name
            )

            # Mantener los roles actuales del usuario local
            odoo_roles = local_employee.roles

        # Verificar si hay cambios que aplicar
        if not has_changes:
            return {
                "success": True,
                "message": "No hay cambios que sincronizar",
                "user_updated": False,
            }

        # Actualizar usuario con datos de Odoo
        updated_user = User(
            id=local_employee.id,
            email=odoo_email,
            full_name=odoo_name,
            is_active=local_employee.is_active,  # Mantener estado actual
            is_superuser=local_employee.is_superuser,  # Mantener estado actual
            roles=odoo_roles,  # Usar roles de Odoo solo si tiene user_id, sino mantener actuales
        )

        # Guardar cambios
        success = self.user_repository.update_user(updated_user)

        if success:
            return {
                "success": True,
                "message": f"Usuario sincronizado exitosamente ({'con roles' if has_user else 'solo nombre/email'})",
                "user_updated": True,
            }
        else:
            return {
                "success": False,
                "message": f"Error al actualizar usuario {local_employee.id} (empleado {employee_id}) en la base de datos",
                "user_updated": False,
            }
