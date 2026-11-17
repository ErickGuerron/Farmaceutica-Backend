"""Importa todos los modelos para que Base.metadata los conozca (Alembic y pruebas)."""
from app.database import Base
from app.models.empleado import empleado
from app.models.usuario import IdentidadProveedor, Rol, Usuario

__all__ = ["Base", "empleado", "IdentidadProveedor", "Rol", "Usuario"]
