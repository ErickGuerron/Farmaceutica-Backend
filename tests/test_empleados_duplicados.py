from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import engine
from app.services.empleado_service import _error_de_duplicado


EMPLEADO = {
    "cedula": "0012345678",
    "nombres": "Ana María",
    "apellidos": "López Vera",
    "correo": "ana@farmacia.test",
    "cargo": "Auxiliar",
    "fecha_contratacion": "2024-01-15",
    "salario": 1200.50,
}


@pytest.fixture
def indices_empleado(app):
    with engine().begin() as conn:
        conn.execute(text("CREATE UNIQUE INDEX UX_Empleado_cedula_0004 ON Empleado (cedula)"))
        conn.execute(text("CREATE UNIQUE INDEX UX_Empleado_correo_0004 ON Empleado (correo) WHERE correo IS NOT NULL"))


@pytest.mark.parametrize(("cambios", "campos"), [
    ({"correo": "otra@farmacia.test"}, ["cedula"]),
    ({"cedula": "1112345678", "correo": " ANA@FARMACIA.TEST "}, ["correo"]),
    ({}, ["cedula", "correo"]),
])
def test_crear_duplicado_identifica_los_campos(client, cabecera_admin, indices_empleado, cambios, campos):
    assert client.post("/empleados", json=EMPLEADO, headers=cabecera_admin).status_code == 201
    respuesta = client.post("/empleados", json={**EMPLEADO, **cambios}, headers=cabecera_admin)
    assert respuesta.status_code == 409
    datos = respuesta.get_json()
    assert datos["mensaje"] == "Empleado ya existe"
    assert datos["codigo"] == "empleado_duplicado"
    assert datos["campos"] == campos
    assert len(client.get("/empleados", headers=cabecera_admin).get_json()) == 1


@pytest.mark.parametrize("campo", ["cedula", "correo"])
def test_solo_gana_un_registro_simultaneo(app, client, cabecera_admin, indices_empleado, campo):
    segundo = dict(EMPLEADO)
    if campo == "cedula":
        segundo["correo"] = "otra@farmacia.test"
    else:
        segundo["cedula"] = "1112345678"
    barrera = Barrier(2, timeout=5)

    def registrar(datos):
        with app.test_client() as proceso:
            barrera.wait()
            respuesta = proceso.post("/empleados", json=datos, headers=cabecera_admin)
            return respuesta.status_code, respuesta.get_json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = sorted(executor.map(registrar, [EMPLEADO, segundo]))
    assert [estado for estado, _ in resultados] == [201, 409]
    assert resultados[1][1]["campos"] == [campo]
    assert len(client.get("/empleados", headers=cabecera_admin).get_json()) == 1


def test_actualizar_con_correo_ajeno_y_crear_sin_correo(client, cabecera_admin, indices_empleado):
    assert client.post("/empleados", json=EMPLEADO, headers=cabecera_admin).status_code == 201
    sin_correo = {**EMPLEADO, "cedula": "1112345678", "correo": None}
    assert client.post("/empleados", json=sin_correo, headers=cabecera_admin).status_code == 201
    assert client.post("/empleados", json={**sin_correo, "cedula": "2112345678", "correo": " "},
                       headers=cabecera_admin).status_code == 201
    filas = client.get("/empleados", headers=cabecera_admin).get_json()
    segundo = next(fila for fila in filas if fila["cedula"] == sin_correo["cedula"])
    ruta = f"/empleados/{segundo['id_empleado']}"
    conflicto = client.put(ruta, json={**segundo, "correo": EMPLEADO["correo"]}, headers=cabecera_admin)
    assert conflicto.status_code == 409
    assert conflicto.get_json()["campos"] == ["correo"]
    assert client.get(ruta, headers=cabecera_admin).get_json()["correo"] is None


@pytest.mark.parametrize("numero", (2601, 2627, 547))
def test_codigos_nativos_de_sql_server(app, numero):
    error = IntegrityError(None, None, Exception("23000", f"[SQL Server] índice 'UX_Empleado_correo_0004'. ({numero}) (SQLExecDirectW)"))
    with engine().connect() as conn:
        conexion = SimpleNamespace(dialect=SimpleNamespace(name="mssql"), execute=conn.execute)
        resultado = _error_de_duplicado(conexion, error, EMPLEADO)
    if numero == 547:
        assert resultado is None
    else:
        assert resultado.campos == ["correo"]
