"""Datos iniciales para desarrollo: usuario admin, usuario empleado y empleados de ejemplo (con Faker).

Es idempotente: si un usuario ya existe no se vuelve a crear, y los empleados de ejemplo solo se generan
cuando la tabla Empleado está vacía (salvo que se indique `forzar_empleados`).
"""
import secrets
from datetime import date, timedelta

from faker import Faker
from sqlalchemy import select

from app.database import sesion
from app.models.usuario import ROL_ADMIN, ROL_EMPLEADO, Usuario
from app.services import empleado_service, usuario_service

CARGOS = [
    "Farmacéutico",
    "Auxiliar de farmacia",
    "Cajero",
    "Bodeguero",
    "Administrador de sucursal",
    "Asesor de ventas",
]


def _existe_usuario(email):
    with sesion() as s:
        return s.scalar(select(Usuario.id_usuario).where(Usuario.email == email.lower())) is not None


def _crear_usuario(nombre, email, password, rol):
    if _existe_usuario(email):
        return {"email": email, "rol": rol, "estado": "ya existía"}
    usuario_service.registrar_local(nombre, email, password, rol)
    return {"email": email, "rol": rol, "estado": "creado"}


def _empleado_falso(fake: Faker):
    fecha = fake.date_between(start_date=date(2018, 1, 1), end_date=date.today() - timedelta(days=1))
    return {
        "cedula": fake.numerify("##########"),
        "nombres": fake.first_name(),
        "apellidos": f"{fake.last_name()} {fake.last_name()}",
        "telefono": fake.numerify("09########"),
        "direccion": fake.address().replace("\n", ", ")[:200],
        "correo": fake.unique.email(),
        "cargo": fake.random_element(CARGOS),
        "fecha_contratacion": fecha.isoformat(),
        "salario": round(fake.pyfloat(min_value=500, max_value=3000, right_digits=2), 2),
        "estado": fake.boolean(chance_of_getting_true=90),
    }


def sembrar(
    admin_email="admin@farmacia.local",
    admin_password=None,
    empleado_email="empleado@farmacia.local",
    empleado_password=None,
    cantidad_empleados=20,
    forzar_empleados=False,
    locale="es_ES",
):
    """Crea los usuarios base y los datos de ejemplo. Devuelve un resumen y las contraseñas generadas."""
    generadas = {}
    if admin_password is None:
        admin_password = secrets.token_urlsafe(12)
        generadas["admin"] = admin_password
    if empleado_password is None:
        empleado_password = secrets.token_urlsafe(12)
        generadas["empleado"] = empleado_password

    usuarios = [
        _crear_usuario("Administrador Demo", admin_email, admin_password, ROL_ADMIN),
        _crear_usuario("Empleado Demo", empleado_email, empleado_password, ROL_EMPLEADO),
    ]

    fake = Faker(locale)
    Faker.seed(0)
    empleados_creados = 0
    if forzar_empleados or not empleado_service.listar():
        for _ in range(cantidad_empleados):
            empleado_service.crear(_empleado_falso(fake))
            empleados_creados += 1

    return {
        "usuarios": usuarios,
        "empleados_creados": empleados_creados,
        "contrasenas_generadas": generadas,
    }
