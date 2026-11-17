from app.services import seed_service, usuario_service
from app.services import empleado_service


def test_seed_crea_admin_empleado_y_datos(app):
    resumen = seed_service.sembrar(admin_password="clave-admin-1", empleado_password="clave-emp-1",
                                   cantidad_empleados=5)

    estados = {u["email"]: (u["rol"], u["estado"]) for u in resumen["usuarios"]}
    assert estados["admin@farmacia.local"] == ("admin", "creado")
    assert estados["empleado@farmacia.local"] == ("empleado", "creado")
    assert resumen["empleados_creados"] == 5
    assert resumen["contrasenas_generadas"] == {}
    assert len(empleado_service.listar()) == 5


def test_seed_es_idempotente(app):
    seed_service.sembrar(admin_password="clave-admin-1", empleado_password="clave-emp-1", cantidad_empleados=3)
    segunda = seed_service.sembrar(admin_password="clave-admin-1", empleado_password="clave-emp-1",
                                   cantidad_empleados=3)

    assert all(u["estado"] == "ya existía" for u in segunda["usuarios"])
    assert segunda["empleados_creados"] == 0
    assert len(empleado_service.listar()) == 3


def test_seed_genera_contrasenas_si_no_se_envian(app):
    resumen = seed_service.sembrar(cantidad_empleados=1)
    assert set(resumen["contrasenas_generadas"]) == {"admin", "empleado"}
    assert all(len(c) >= 12 for c in resumen["contrasenas_generadas"].values())

    login = usuario_service.autenticar("admin@farmacia.local", resumen["contrasenas_generadas"]["admin"])
    assert login is not None and login["rol"] == "admin"
