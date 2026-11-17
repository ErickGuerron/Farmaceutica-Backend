"""Tabla Empleado existente en SQL Server.

El acceso a esta tabla usa SQL explícito (ver app/services/empleado_service.py) para conservar
exactamente el comportamiento de control de concurrencia por row_version. Este mapeo solo describe
la tabla para Alembic y para las pruebas.
"""
from sqlalchemy import Boolean, Column, Date, Integer, Numeric, String, TIMESTAMP, Table

from app.database import Base

empleado = Table(
    "Empleado",
    Base.metadata,
    Column("id_empleado", Integer, primary_key=True, autoincrement=True),
    Column("cedula", String(10), nullable=False),
    Column("nombres", String(100), nullable=False),
    Column("apellidos", String(100), nullable=False),
    Column("telefono", String(20)),
    Column("direccion", String(200)),
    Column("correo", String(150)),
    Column("cargo", String(100), nullable=False),
    Column("fecha_contratacion", Date, nullable=False),
    Column("salario", Numeric(10, 2), nullable=False),
    Column("estado", Boolean, nullable=False),
    Column("row_version", TIMESTAMP, nullable=False),
)
