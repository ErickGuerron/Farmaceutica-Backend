from flask import Blueprint, jsonify, request

from app.security.decorators import requiere_admin, requiere_lectura_empleados
from app.services import empleado_service as servicio
from app.services.versiones import codificar_version, decodificar_version

bp = Blueprint("empleados", __name__)


def _mensaje(texto, status):
    return jsonify({"mensaje": texto}), status


def _version_valida(valor):
    """Devuelve los bytes del rowversion o None si falta o es inválido."""
    version = decodificar_version(valor)
    if version is None or len(version) != 8:
        return None
    return version


# CREATE - REGISTRAR EMPLEADO

@bp.route("/empleados", methods=["POST"])
@requiere_admin
def crear():
    data = request.get_json()
    servicio.crear(data)
    return _mensaje("Empleado registrado correctamente", 201)


# READ - LISTAR EMPLEADOS

@bp.route("/empleados", methods=["GET"])
@requiere_lectura_empleados
def listar():
    return jsonify(servicio.listar())


# READ - BUSCAR EMPLEADO POR ID

@bp.route("/empleados/<int:id>", methods=["GET"])
@requiere_lectura_empleados
def buscar(id):
    empleado = servicio.buscar(id)
    if empleado is None:
        return _mensaje("Empleado no encontrado", 404)
    return jsonify(empleado)


# UPDATE - ACTUALIZAR CON CONCURRENCIA

@bp.route("/empleados/<int:id>", methods=["PUT"])
@requiere_admin
def actualizar(id):
    data = request.get_json()

    if not data or not data.get("version"):
        return _mensaje("Debe enviar la version del empleado", 400)

    version = _version_valida(data["version"])
    if version is None:
        return _mensaje("Version invalida", 400)

    resultado, nueva_version = servicio.actualizar(id, data, version)

    if resultado == servicio.NO_ENCONTRADO:
        return _mensaje("Empleado no encontrado", 404)

    if resultado == servicio.CONFLICTO:
        return jsonify({
            "mensaje": "Conflicto de concurrencia",
            "detalle": "Otro usuario modifico este empleado. Consulte nuevamente los datos antes de actualizar."
        }), 409

    return jsonify({
        "mensaje": "Empleado actualizado correctamente",
        "version": codificar_version(nueva_version)
    }), 200


# DELETE - ELIMINAR CON CONCURRENCIA

@bp.route("/empleados/<int:id>", methods=["DELETE"])
@requiere_admin
def eliminar(id):
    data = request.get_json(silent=True) or {}

    if not data.get("version"):
        return _mensaje("Debe enviar la version del empleado", 400)

    version = _version_valida(data["version"])
    if version is None:
        return _mensaje("Version invalida", 400)

    resultado = servicio.eliminar(id, version)

    if resultado == servicio.NO_ENCONTRADO:
        return _mensaje("Empleado no encontrado", 404)

    if resultado == servicio.CONFLICTO:
        return jsonify({
            "mensaje": "Conflicto de concurrencia",
            "detalle": "El empleado fue modificado por otro usuario. No se puede eliminar con una version antigua."
        }), 409

    return _mensaje("Empleado eliminado correctamente", 200)
