import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Carga el archivo .env de la raíz del proyecto (no sobrescribe variables ya definidas en el sistema).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _env(nombre, defecto=None):
    valor = os.environ.get(nombre, defecto)
    return valor if valor not in (None, "") else defecto


def construir_database_url():
    """DATABASE_URL tiene prioridad; si no, se arma desde DB_ODBC_CONNECTION (SQL Server)."""
    url = _env("DATABASE_URL")
    if url:
        return url

    odbc = _env("DB_ODBC_CONNECTION")
    if not odbc:
        raise RuntimeError("Defina DATABASE_URL o DB_ODBC_CONNECTION")

    return URL.create("mssql+pyodbc", query={"odbc_connect": odbc}).render_as_string(hide_password=False)


class Config:
    def __init__(self):
        self.database_url = construir_database_url()

        self.jwt_secret = _env("JWT_SECRET")
        if not self.jwt_secret:
            raise RuntimeError("Defina JWT_SECRET")
        self.jwt_expira_horas = int(_env("JWT_EXPIRA_HORAS", "8"))

        self.oauth_redirect_base = _env("OAUTH_REDIRECT_BASE", "http://localhost:5000").rstrip("/")
        self.oauth_frontend_returns = frozenset(valor.strip() for valor in
            _env("OAUTH_FRONTEND_RETURNS", "").split(",") if valor.strip())

        self.google_client_id = _env("GOOGLE_CLIENT_ID")
        self.google_client_secret = _env("GOOGLE_CLIENT_SECRET")

        self.facebook_app_id = _env("FACEBOOK_APP_ID")
        self.facebook_app_secret = _env("FACEBOOK_APP_SECRET")
        self.facebook_graph_version = _env("FACEBOOK_GRAPH_VERSION", "v21.0")

        self.instagram_app_id = _env("INSTAGRAM_APP_ID")
        self.instagram_app_secret = _env("INSTAGRAM_APP_SECRET")

        self.ports = parsear_puertos(_env("PORTS") or _env("PORT", "5000"))


def parsear_puertos(texto):
    """'5000,5001' -> [5000, 5001]. Sin puertos repetidos ni valores fuera de rango."""
    puertos = []
    for pieza in texto.split(","):
        pieza = pieza.strip()
        if not pieza:
            continue
        puerto = int(pieza)
        if not 1 <= puerto <= 65535:
            raise RuntimeError(f"Puerto fuera de rango: {puerto}")
        if puerto in puertos:
            raise RuntimeError(f"Puerto repetido: {puerto}")
        puertos.append(puerto)
    if not puertos:
        raise RuntimeError("Defina al menos un puerto en PORTS")
    return puertos
