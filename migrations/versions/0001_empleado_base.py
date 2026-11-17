"""Tabla Empleado (base existente).

En bases que ya tienen la tabla Empleado, esta migración no hace nada. Para marcar una base existente
como actualizada sin ejecutar esta migración use: `alembic stamp 0001`.

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        IF OBJECT_ID(N'dbo.Empleado', N'U') IS NULL
        CREATE TABLE dbo.Empleado (
            id_empleado        INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Empleado PRIMARY KEY,
            cedula             NVARCHAR(10)   NOT NULL,
            nombres            NVARCHAR(100)  NOT NULL,
            apellidos          NVARCHAR(100)  NOT NULL,
            telefono           NVARCHAR(20)   NULL,
            direccion          NVARCHAR(200)  NULL,
            correo             NVARCHAR(150)  NULL,
            cargo              NVARCHAR(100)  NOT NULL,
            fecha_contratacion DATE           NOT NULL,
            salario            DECIMAL(10,2)  NOT NULL,
            estado             BIT            NOT NULL,
            row_version        ROWVERSION     NOT NULL
        )
    """)


def downgrade() -> None:
    # No se elimina la tabla: contiene datos de producción que existían antes de Alembic.
    pass
