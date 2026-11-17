from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ROL_ADMIN = "admin"
ROL_EMPLEADO = "empleado"
ROLES_VALIDOS = (ROL_ADMIN, ROL_EMPLEADO)

PROVEEDORES = ("google", "facebook", "instagram")


class Rol(Base):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        Index(
            "ux_usuario_email",
            "email",
            unique=True,
            mssql_where=text("email IS NOT NULL"),
            sqlite_where=text("email IS NOT NULL"),
        ),
    )

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    rol: Mapped[Rol] = relationship(lazy="joined")
    identidades: Mapped[list["IdentidadProveedor"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class IdentidadProveedor(Base):
    """Vincula un usuario con una cuenta de Google, Facebook o Instagram."""

    __tablename__ = "identidad_proveedor"
    __table_args__ = (UniqueConstraint("proveedor", "proveedor_uid", name="uq_identidad_proveedor"),)

    id_identidad: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False)
    proveedor: Mapped[str] = mapped_column(String(20), nullable=False)
    proveedor_uid: Mapped[str] = mapped_column(String(255), nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="identidades")
