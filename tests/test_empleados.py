import base64

EMPLEADO = {
    "cedula": "1712345678",
    "nombres": "Ana",
    "apellidos": "Lopez",
    "telefono": "0999999999",
    "direccion": "Quito",
    "correo": "ana@farmacia.test",
    "cargo": "Farmaceutica",
    "fecha_contratacion": "2024-01-15",
    "salario": 1200.5,
}


def test_raiz_y_marca_de_instancia(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert respuesta.get_json()["mensaje"] == "API Farmaceutica activa"
    assert "X-Servidor" in respuesta.headers
    assert "atendido_por" in respuesta.get_json()


def test_listar_requiere_sesion(client):
    assert client.get("/empleados").status_code == 401


def test_empleado_puede_leer_pero_no_escribir(client, cabecera_empleado):
    assert client.post("/empleados", json=EMPLEADO, headers=cabecera_empleado).status_code == 403
    assert client.get("/empleados", headers=cabecera_empleado).status_code == 200


def test_crud_con_admin_mantiene_estructura(client, cabecera_admin):
    respuesta = client.post("/empleados", json=EMPLEADO, headers=cabecera_admin)
    assert respuesta.status_code == 201
    assert respuesta.get_json()["mensaje"] == "Empleado registrado correctamente"

    lista = client.get("/empleados", headers=cabecera_admin).get_json()
    assert len(lista) == 1
    empleado = lista[0]
    assert set(empleado) >= {
        "id_empleado", "cedula", "nombres", "apellidos", "telefono", "direccion",
        "correo", "cargo", "fecha_contratacion", "salario", "estado", "version",
    }
    assert empleado["fecha_contratacion"] == "2024-01-15"
    assert empleado["salario"] == 1200.5
    assert empleado["estado"] is True
    assert base64.b64decode(empleado["version"]) == b"\x00\x00\x00\x00\x00\x00\x00\x01"

    id_empleado = empleado["id_empleado"]
    detalle = client.get(f"/empleados/{id_empleado}", headers=cabecera_admin).get_json()
    assert "atendido_por" in detalle
    detalle.pop("atendido_por")
    assert detalle == empleado

    actualizacion = dict(EMPLEADO, nombres="Ana Maria", version=empleado["version"])
    respuesta = client.put(f"/empleados/{id_empleado}", json=actualizacion, headers=cabecera_admin)
    assert respuesta.status_code == 200
    assert respuesta.get_json()["mensaje"] == "Empleado actualizado correctamente"
    assert "version" in respuesta.get_json()

    respuesta = client.delete(f"/empleados/{id_empleado}", json={"version": empleado["version"]},
                              headers=cabecera_admin)
    assert respuesta.status_code == 200
    assert respuesta.get_json()["mensaje"] == "Empleado eliminado correctamente"
    assert client.get(f"/empleados/{id_empleado}", headers=cabecera_admin).status_code == 404


def test_errores_de_validacion_y_no_encontrado(client, cabecera_admin):
    respuesta = client.get("/empleados/999", headers=cabecera_admin)
    assert respuesta.status_code == 404
    assert respuesta.get_json()["mensaje"] == "Empleado no encontrado"

    sin_version = client.put("/empleados/1", json=EMPLEADO, headers=cabecera_admin)
    assert sin_version.status_code == 400
    assert sin_version.get_json()["mensaje"] == "Debe enviar la version del empleado"

    version_invalida = client.put("/empleados/1", json=dict(EMPLEADO, version="no-base64!"),
                                  headers=cabecera_admin)
    assert version_invalida.status_code == 400
    assert version_invalida.get_json()["mensaje"] == "Version invalida"

    borrar_sin_version = client.delete("/empleados/1", json={}, headers=cabecera_admin)
    assert borrar_sin_version.status_code == 400

    actualizar_inexistente = client.put("/empleados/999", json=dict(EMPLEADO, version=base64.b64encode(b"12345678").decode()),
                                        headers=cabecera_admin)
    assert actualizar_inexistente.status_code == 404
