"""Roles, usuarios e identidades de proveedores OAuth.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE dbo.rol (
            id_rol  INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_rol PRIMARY KEY,
            nombre  NVARCHAR(30)      NOT NULL CONSTRAINT uq_rol_nombre UNIQUE
        )
    """)

    op.execute("""
        INSERT INTO dbo.rol (nombre) VALUES (N'admin'), (N'empleado')
    """)

    op.execute("""
        CREATE TABLE dbo.usuario (
            id_usuario      INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_usuario PRIMARY KEY,
            nombre          NVARCHAR(150)     NOT NULL,
            email           NVARCHAR(255)     NULL,
            password_hash   NVARCHAR(255)     NULL,
            id_rol          INT               NOT NULL CONSTRAINT FK_usuario_rol REFERENCES dbo.rol (id_rol),
            activo          BIT               NOT NULL CONSTRAINT DF_usuario_activo DEFAULT 1,
            fecha_creacion  DATETIME          NOT NULL CONSTRAINT DF_usuario_fecha DEFAULT GETDATE()
        )
    """)

    # Unicidad de correo solo cuando existe: las cuentas de Instagram no tienen correo.
    op.execute("""
        CREATE UNIQUE INDEX ux_usuario_email ON dbo.usuario (email)
        WHERE email IS NOT NULL
    """)

    op.execute("""
        CREATE TABLE dbo.identidad_proveedor (
            id_identidad   INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_identidad_proveedor PRIMARY KEY,
            id_usuario     INT               NOT NULL CONSTRAINT FK_identidad_usuario REFERENCES dbo.usuario (id_usuario),
            proveedor      NVARCHAR(20)      NOT NULL,
            proveedor_uid  NVARCHAR(255)     NOT NULL,
            CONSTRAINT uq_identidad_proveedor UNIQUE (proveedor, proveedor_uid)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE dbo.identidad_proveedor")
    op.execute("DROP INDEX ux_usuario_email ON dbo.usuario")
    op.execute("DROP TABLE dbo.usuario")
    op.execute("DROP TABLE dbo.rol")
