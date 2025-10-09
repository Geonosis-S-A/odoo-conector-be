from datetime import date
from typing import List, Optional
from sqlmodel import select, Session
from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository
from app.employee_price.infra.db.models import EmployeePriceModel


class SQLModelEmployeePriceRepository(EmployeePriceRepository):
    """Implementación del repositorio de precios de empleados usando SQLModel"""

    def __init__(self, db: Session):
        self.db = db

    def _model_to_domain(self, model: EmployeePriceModel) -> EmployeePrice:
        """Convierte un modelo de DB a entidad de dominio"""
        return EmployeePrice(
            id=model.id,
            user_id=model.user_id,
            cost_per_hour=model.cost_per_hour,
            date_from=model.date_from,
            date_to=model.date_to,
        )

    def _domain_to_model(self, domain: EmployeePrice) -> EmployeePriceModel:
        """Convierte una entidad de dominio a modelo de DB"""
        return EmployeePriceModel(
            id=domain.id,
            user_id=domain.user_id,
            cost_per_hour=domain.cost_per_hour,
            date_from=domain.date_from,
            date_to=domain.date_to,
        )

    def save(self, employee_price: EmployeePrice) -> EmployeePrice:
        """Guarda un nuevo registro de precio de empleado"""
        model = self._domain_to_model(employee_price)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_domain(model)

    def get_by_id(self, id: int) -> Optional[EmployeePrice]:
        """Obtiene un registro por su ID"""
        statement = select(EmployeePriceModel).where(EmployeePriceModel.id == id)
        model = self.db.exec(statement).first()
        if model is None:
            return None
        return self._model_to_domain(model)

    def get_by_user_id(self, user_id: int) -> List[EmployeePrice]:
        """Obtiene todos los registros de precio de un usuario"""
        statement = (
            select(EmployeePriceModel)
            .where(EmployeePriceModel.user_id == user_id)
            .order_by(EmployeePriceModel.date_from.desc())
        )
        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]

    def get_active_by_user_id(
        self, user_id: int, check_date: Optional[date] = None
    ) -> Optional[EmployeePrice]:
        """
        Obtiene el precio activo de un usuario en una fecha específica.
        Si no se proporciona fecha, usa la fecha actual.
        """
        if check_date is None:
            check_date = date.today()

        statement = (
            select(EmployeePriceModel)
            .where(
                EmployeePriceModel.user_id == user_id,
                EmployeePriceModel.date_from <= check_date,
            )
            .where(
                (EmployeePriceModel.date_to.is_(None))
                | (EmployeePriceModel.date_to >= check_date)
            )
            .order_by(EmployeePriceModel.date_from.desc())
        )

        model = self.db.exec(statement).first()
        if model is None:
            return None
        return self._model_to_domain(model)

    def get_open_record_by_user_id(self, user_id: int) -> Optional[EmployeePrice]:
        """
        Obtiene el registro abierto (sin date_to) de un usuario.
        Este método es útil para encontrar el registro que debe cerrarse
        al crear un nuevo registro de precio.
        
        Returns:
            El registro con date_to = NULL si existe, None en caso contrario
        """
        statement = (
            select(EmployeePriceModel)
            .where(
                EmployeePriceModel.user_id == user_id,
                EmployeePriceModel.date_to.is_(None)
            )
            .order_by(EmployeePriceModel.date_from.desc())
        )

        model = self.db.exec(statement).first()
        if model is None:
            return None
        return self._model_to_domain(model)

    def get_all(self) -> List[EmployeePrice]:
        """Obtiene todos los registros de precios"""
        statement = select(EmployeePriceModel).order_by(
            EmployeePriceModel.date_from.desc()
        )
        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]

    def update(self, employee_price: EmployeePrice) -> bool:
        """Actualiza un registro existente"""
        if employee_price.id is None:
            return False

        statement = select(EmployeePriceModel).where(
            EmployeePriceModel.id == employee_price.id
        )
        model = self.db.exec(statement).first()
        if model is None:
            return False

        # Actualizar campos
        model.user_id = employee_price.user_id
        model.cost_per_hour = employee_price.cost_per_hour
        model.date_from = employee_price.date_from
        model.date_to = employee_price.date_to

        self.db.commit()
        self.db.refresh(model)
        return True

    def delete(self, id: int) -> bool:
        """Elimina un registro por su ID"""
        statement = select(EmployeePriceModel).where(EmployeePriceModel.id == id)
        model = self.db.exec(statement).first()
        if model is None:
            return False

        self.db.delete(model)
        self.db.commit()
        return True

    def get_all_active(self, check_date: Optional[date] = None) -> List[EmployeePrice]:
        """
        Obtiene todos los precios activos en una fecha específica.
        Si no se proporciona fecha, usa la fecha actual.
        """
        if check_date is None:
            check_date = date.today()

        statement = (
            select(EmployeePriceModel)
            .where(EmployeePriceModel.date_from <= check_date)
            .where(
                (EmployeePriceModel.date_to.is_(None))
                | (EmployeePriceModel.date_to >= check_date)
            )
            .order_by(EmployeePriceModel.user_id, EmployeePriceModel.date_from.desc())
        )

        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]

