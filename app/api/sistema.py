import socket

from flask import Blueprint, jsonify, request

bp = Blueprint("sistema", __name__)

HOSTNAME = socket.gethostname()


def instancia():
    return {"servidor": HOSTNAME, "puerto": request.environ.get("SERVER_PORT")}


@bp.route("/", methods=["GET"])
def raiz():
    return jsonify({"mensaje": "API Farmaceutica activa"}), 200


@bp.route("/instancia", methods=["GET"])
def ver_instancia():
    return jsonify(instancia()), 200


@bp.after_app_request
def marcar_instancia(response):
    """Agrega a cada respuesta el servidor que la atendió (encabezados y cuerpo JSON)."""
    info = instancia()
    response.headers["X-Servidor"] = info["servidor"]
    response.headers["X-Puerto"] = str(info["puerto"])
    if response.is_json:
        body = response.get_json(silent=True)
        if isinstance(body, dict) and "atendido_por" not in body and "servidor" not in body:
            body["atendido_por"] = info
            response.set_data(jsonify(body).get_data())
    return response
