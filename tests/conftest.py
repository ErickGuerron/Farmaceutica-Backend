import pytest
from sqlalchemy import text

from app import create_app, database
from app.config import Config
from app.models import Base


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + (tmp_path / "test.db").as_posix())
    monkeypatch.setenv("JWT_SECRET", "secreto-de-prueba-con-mas-de-32-caracteres-x")
    monkeypatch.setenv("OAUTH_REDIRECT_BASE", "http://api.test")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv("FACEBOOK_APP_ID", "fb-id")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "fb-secret")
    monkeypatch.setenv("INSTAGRAM_APP_ID", "ig-id")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "ig-secret")
    monkeypatch.delenv("DB_ODBC_CONNECTION", raising=False)
    return Config()


@pytest.fixture
def app(settings):
    application = create_app(settings)
    motor = database.engine()
    Base.metadata.create_all(motor)

    # SQLite no tiene ROWVERSION: se simula con un valor por defecto para que los inserts funcionen.
    # La concurrencia real por row_version solo se valida contra SQL Server.
    with motor.begin() as conn:
        conn.execute(text('DROP TABLE "Empleado"'))
        conn.execute(text("""
            CREATE TABLE "Empleado" (
                id_empleado INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula VARCHAR(10) NOT NULL,
                nombres VARCHAR(100) NOT NULL,
                apellidos VARCHAR(100) NOT NULL,
                telefono VARCHAR(20),
                direccion VARCHAR(200),
                correo VARCHAR(150),
                cargo VARCHAR(100) NOT NULL,
                fecha_contratacion DATE NOT NULL,
                salario NUMERIC(10,2) NOT NULL,
                estado BOOLEAN NOT NULL,
                row_version BLOB NOT NULL DEFAULT X'0000000000000001'
            )
        """))
        conn.execute(text("INSERT INTO rol (nombre) VALUES ('admin'), ('empleado')"))

    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def token_de(client):
    """Crea un usuario con el rol indicado, inicia sesión y devuelve su token."""
    from app.services import usuario_service

    def _crear(rol, email):
        usuario = usuario_service.registrar_local("Usuario " + rol, email, "clave-segura-1")
        if rol != "empleado":
            usuario_service.asignar_rol(usuario["id_usuario"], rol)
        respuesta = client.post("/auth/login", json={"email": email, "password": "clave-segura-1"})
        assert respuesta.status_code == 200, respuesta.get_json()
        return respuesta.get_json()["access_token"]

    return _crear


@pytest.fixture
def cabecera_admin(token_de):
    return {"Authorization": "Bearer " + token_de("admin", "admin@farmacia.test")}


@pytest.fixture
def cabecera_empleado(token_de):
    return {"Authorization": "Bearer " + token_de("empleado", "empleado@farmacia.test")}
