"""Usuarios, roles, contraseñas y vínculos con proveedores OAuth."""
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import sesion
from app.errors import ErrorAplicacion
from app.models.usuario import PROVEEDORES, ROL_ADMIN, ROL_EMPLEADO, ROLES_VALIDOS, IdentidadProveedor, Rol, Usuario


def serializar_usuario(usuario: Usuario):
    return {
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol.nombre,
        "activo": bool(usuario.activo),
        "proveedores": sorted(i.proveedor for i in usuario.identidades),
    }


def _normalizar_email(email):
    return email.strip().lower() if email else None


def _rol_id(s, nombre):
    rol = s.scalar(select(Rol).where(Rol.nombre == nombre))
    if rol is None:
        raise ErrorAplicacion(f"Rol '{nombre}' no existe; ejecute las migraciones", status=500)
    return rol.id_rol


def _crear(s, nombre, email, password, rol):
    usuario = Usuario(
        nombre=nombre,
        email=email,
        password_hash=generate_password_hash(password) if password else None,
        id_rol=_rol_id(s, rol),
        activo=True,
    )
    s.add(usuario)
    s.flush()
    return usuario


def registrar_local(nombre, email, password, rol=ROL_EMPLEADO):
    email = _normalizar_email(email)
    with sesion() as s:
        if s.scalar(select(Usuario.id_usuario).where(Usuario.email == email)) is not None:
            raise ErrorAplicacion("Ya existe un usuario con ese correo", status=409)
        usuario = _crear(s, nombre, email, password, rol)
        s.commit()
        s.refresh(usuario)
        return serializar_usuario(usuario)


def autenticar(email, password):
    """Devuelve el usuario si las credenciales son válidas y la cuenta está activa; si no, None."""
    email = _normalizar_email(email)
    if not email or not password:
        return None
    with sesion() as s:
        usuario = s.scalar(select(Usuario).where(Usuario.email == email))
        if usuario is None or not usuario.password_hash:
            return None
        if not check_password_hash(usuario.password_hash, password):
            return None
        if not usuario.activo:
            raise ErrorAplicacion("La cuenta está desactivada", status=403)
        return serializar_usuario(usuario)


def obtener_usuario(id_usuario):
    with sesion() as s:
        usuario = s.get(Usuario, id_usuario)
        return None if usuario is None else serializar_usuario(usuario)


def listar_usuarios():
    with sesion() as s:
        return [serializar_usuario(u) for u in s.scalars(select(Usuario).order_by(Usuario.id_usuario))]


def asignar_rol(id_usuario, rol):
    if rol not in ROLES_VALIDOS:
        raise ErrorAplicacion(f"Rol inválido. Valores permitidos: {', '.join(ROLES_VALIDOS)}")
    with sesion() as s:
        usuario = s.get(Usuario, id_usuario)
        if usuario is None:
            raise ErrorAplicacion("Usuario no encontrado", status=404)
        usuario.id_rol = _rol_id(s, rol)
        s.commit()
        s.refresh(usuario)
        return serializar_usuario(usuario)


def login_oauth(proveedor, proveedor_uid, nombre, email=None, email_verificado=False):
    """Busca o crea el usuario para una identidad de proveedor.

    1. Si la identidad ya está vinculada, se usa ese usuario.
    2. Si el proveedor entrega un correo verificado que ya existe, se vincula a esa cuenta.
    3. Si no, se crea un usuario con rol empleado.
    """
    if proveedor not in PROVEEDORES:
        raise ErrorAplicacion("Proveedor no soportado", status=404)

    email = _normalizar_email(email) if email_verificado else None

    with sesion() as s:
        identidad = s.scalar(
            select(IdentidadProveedor).where(
                IdentidadProveedor.proveedor == proveedor,
                IdentidadProveedor.proveedor_uid == str(proveedor_uid),
            )
        )

        if identidad is not None:
            usuario = s.get(Usuario, identidad.id_usuario)
        else:
            usuario = s.scalar(select(Usuario).where(Usuario.email == email)) if email else None
            if usuario is None:
                usuario = _crear(s, nombre or email or f"{proveedor}-{proveedor_uid}", email, None, ROL_EMPLEADO)
            s.add(IdentidadProveedor(id_usuario=usuario.id_usuario, proveedor=proveedor,
                                     proveedor_uid=str(proveedor_uid)))

        if not usuario.activo:
            raise ErrorAplicacion("La cuenta está desactivada", status=403)

        s.commit()
        s.refresh(usuario)
        return serializar_usuario(usuario)


def crear_admin(nombre, email, password):
    """Usado por el comando `python main.py crear-admin`."""
    email = _normalizar_email(email)
    with sesion() as s:
        if s.scalar(select(Usuario.id_usuario).where(Usuario.email == email)) is not None:
            raise ErrorAplicacion("Ya existe un usuario con ese correo", status=409)
        usuario = _crear(s, nombre, email, password, ROL_ADMIN)
        s.commit()
        s.refresh(usuario)
        return serializar_usuario(usuario)
