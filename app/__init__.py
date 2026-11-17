from flask import Flask, jsonify
from flask_cors import CORS

from app import database
from app.api import auth, empleados, sistema
from app.config import Config
from app.errors import ErrorAplicacion


def create_app(settings: Config | None = None):
    settings = settings or Config()

    app = Flask(__name__)
    app.config["SETTINGS"] = settings

    database.inicializar(settings.database_url)

    CORS(app, expose_headers=["X-Servidor", "X-Puerto"])

    app.register_blueprint(sistema.bp)
    app.register_blueprint(empleados.bp)
    app.register_blueprint(auth.bp)

    @app.errorhandler(ErrorAplicacion)
    def manejar_error_aplicacion(error):
        cuerpo = {"mensaje": error.mensaje}
        if error.detalle:
            cuerpo["detalle"] = error.detalle
        return jsonify(cuerpo), error.status

    return app
