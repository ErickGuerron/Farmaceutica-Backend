"""Acceso a la tabla Empleado.

Las consultas y el control de concurrencia (row_version) son las mismas que tenía api-farmaceutica.py,
para que la forma de los datos y los códigos de respuesta no cambien.
"""
from sqlalchemy import text

from app.database import engine
from app.services.versiones import codificar_version

COLUMNAS = """
    id_empleado, cedula, nombres, apellidos,
    telefono, direccion, correo, cargo,
    fecha_contratacion, salario, estado, row_version
"""

SQL_INSERTAR = text("""
    INSERT INTO Empleado
    (cedula, nombres, apellidos, telefono, direccion,
     correo, cargo, fecha_contratacion, salario, estado)
    VALUES (:cedula, :nombres, :apellidos, :telefono, :direccion,
            :correo, :cargo, :fecha_contratacion, :salario, :estado)
""")

SQL_LISTAR = text(f"SELECT {COLUMNAS} FROM Empleado")

SQL_BUSCAR = text(f"SELECT {COLUMNAS} FROM Empleado WHERE id_empleado = :id")

SQL_ACTUALIZAR = text("""
    UPDATE Empleado SET
        cedula = :cedula,
        nombres = :nombres,
        apellidos = :apellidos,
        telefono = :telefono,
        direccion = :direccion,
        correo = :correo,
        cargo = :cargo,
        fecha_contratacion = :fecha_contratacion,
        salario = :salario,
        estado = :estado
    WHERE id_empleado = :id
    AND row_version = :version
""")

SQL_ELIMINAR = text("""
    DELETE FROM Empleado
    WHERE id_empleado = :id
    AND row_version = :version
""")

SQL_EXISTE = text("SELECT 1 FROM Empleado WHERE id_empleado = :id")

SQL_VERSION = text("SELECT row_version FROM Empleado WHERE id_empleado = :id")

# Resultados de actualizar/eliminar cuando no se completa la operación
NO_ENCONTRADO = "no_encontrado"
CONFLICTO = "conflicto"


def _parametros_empleado(data):
    return {
        "cedula": data["cedula"],
        "nombres": data["nombres"],
        "apellidos": data["apellidos"],
        "telefono": data.get("telefono"),
        "direccion": data.get("direccion"),
        "correo": data.get("correo"),
        "cargo": data["cargo"],
        "fecha_contratacion": data["fecha_contratacion"],
        "salario": data["salario"],
        "estado": data.get("estado", True),
    }


def serializar_empleado(row):
    return {
        "id_empleado": row[0],
        "cedula": row[1],
        "nombres": row[2],
        "apellidos": row[3],
        "telefono": row[4],
        "direccion": row[5],
        "correo": row[6],
        "cargo": row[7],
        "fecha_contratacion": str(row[8]),
        "salario": float(row[9]),
        "estado": bool(row[10]),
        "version": codificar_version(row[11])
    }


def crear(data):
    with engine().connect() as conn:
        try:
            conn.execute(SQL_INSERTAR, _parametros_empleado(data))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def listar():
    with engine().connect() as conn:
        return [serializar_empleado(row) for row in conn.execute(SQL_LISTAR).fetchall()]


def buscar(id):
    with engine().connect() as conn:
        row = conn.execute(SQL_BUSCAR, {"id": id}).first()
        return None if row is None else serializar_empleado(row)


def actualizar(id, data, version):
    """Devuelve (resultado, version_nueva). resultado es 'ok', NO_ENCONTRADO o CONFLICTO."""
    parametros = _parametros_empleado(data)
    parametros.update({"id": id, "version": version})

    with engine().connect() as conn:
        try:
            resultado = conn.execute(SQL_ACTUALIZAR, parametros)

            if resultado.rowcount == 0:
                conn.rollback()
                if conn.execute(SQL_EXISTE, {"id": id}).first() is None:
                    return NO_ENCONTRADO, None
                return CONFLICTO, None

            conn.commit()
            nueva_version = conn.execute(SQL_VERSION, {"id": id}).scalar()
            return "ok", nueva_version

        except Exception:
            conn.rollback()
            raise


def eliminar(id, version):
    """Devuelve 'ok', NO_ENCONTRADO o CONFLICTO."""
    with engine().connect() as conn:
        try:
            resultado = conn.execute(SQL_ELIMINAR, {"id": id, "version": version})

            if resultado.rowcount == 0:
                conn.rollback()
                if conn.execute(SQL_EXISTE, {"id": id}).first() is None:
                    return NO_ENCONTRADO
                return CONFLICTO

            conn.commit()
            return "ok"

        except Exception:
            conn.rollback()
            raise
