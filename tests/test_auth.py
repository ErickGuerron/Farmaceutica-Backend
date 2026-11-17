from urllib.parse import parse_qs, urlparse

import pytest

from app.services import oauth_service, usuario_service


def test_registro_crea_empleado_y_login_devuelve_token(client):
    respuesta = client.post("/auth/registro", json={
        "nombre": "Luis", "email": "Luis@Farmacia.test", "password": "clave-segura-1",
    })
    assert respuesta.status_code == 201
    assert respuesta.get_json()["usuario"]["rol"] == "empleado"
    assert respuesta.get_json()["usuario"]["email"] == "luis@farmacia.test"

    login = client.post("/auth/login", json={"email": "luis@farmacia.test", "password": "clave-segura-1"})
    assert login.status_code == 200
    datos = login.get_json()
    assert datos["token_type"] == "Bearer"
    assert datos["expires_in"] > 0
    assert datos["usuario"]["rol"] == "empleado"

    perfil = client.get("/auth/me", headers={"Authorization": "Bearer " + datos["access_token"]})
    assert perfil.status_code == 200
    assert perfil.get_json()["email"] == "luis@farmacia.test"


def test_registro_valida_datos_y_no_duplica(client):
    corta = client.post("/auth/registro", json={"nombre": "A", "email": "a@x.test", "password": "corta"})
    assert corta.status_code == 400

    client.post("/auth/registro", json={"nombre": "A", "email": "a@x.test", "password": "clave-segura-1"})
    repetido = client.post("/auth/registro", json={"nombre": "B", "email": "a@x.test", "password": "clave-segura-1"})
    assert repetido.status_code == 409


def test_login_con_credenciales_incorrectas(client):
    client.post("/auth/registro", json={"nombre": "A", "email": "a@x.test", "password": "clave-segura-1"})
    assert client.post("/auth/login", json={"email": "a@x.test", "password": "otra"}).status_code == 401
    assert client.post("/auth/login", json={"email": "nadie@x.test", "password": "clave-segura-1"}).status_code == 401


def test_cuenta_desactivada_no_puede_usar_token(client, token_de):
    token = token_de("empleado", "temp@farmacia.test")
    from app.database import sesion
    from app.models.usuario import Usuario
    with sesion() as s:
        usuario = s.query(Usuario).filter_by(email="temp@farmacia.test").one()
        usuario.activo = False
        s.commit()

    respuesta = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert respuesta.status_code == 401


def test_token_invalido_o_ausente(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_solo_admin_cambia_roles(client, cabecera_admin, cabecera_empleado):
    usuario = usuario_service.registrar_local("Pepe", "pepe@farmacia.test", "clave-segura-1")
    url = f"/auth/usuarios/{usuario['id_usuario']}/rol"

    assert client.put(url, json={"rol": "admin"}, headers=cabecera_empleado).status_code == 403

    respuesta = client.put(url, json={"rol": "admin"}, headers=cabecera_admin)
    assert respuesta.status_code == 200
    assert respuesta.get_json()["usuario"]["rol"] == "admin"

    invalido = client.put(url, json={"rol": "superusuario"}, headers=cabecera_admin)
    assert invalido.status_code == 400


def test_login_google_devuelve_url_con_state(client):
    respuesta = client.get("/auth/google/login")
    assert respuesta.status_code == 200
    url = urlparse(respuesta.get_json()["authorization_url"])
    params = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert params["client_id"] == ["google-id"]
    assert params["redirect_uri"] == ["http://api.test/auth/google/callback"]
    assert params["state"][0]


def test_proveedor_no_soportado_y_no_configurado(client):
    assert client.get("/auth/twitter/login").status_code == 404

    client.application.config["SETTINGS"].instagram_app_id = None
    assert client.get("/auth/instagram/login").status_code == 503


def test_callback_rechaza_state_manipulado(client):
    respuesta = client.get("/auth/google/callback?code=abc&state=falso")
    assert respuesta.status_code == 400


def test_callback_cancelado(client):
    assert client.get("/auth/facebook/callback?error=access_denied").status_code == 400


def _state(client, proveedor):
    url = client.get(f"/auth/{proveedor}/login").get_json()["authorization_url"]
    return parse_qs(urlparse(url).query)["state"][0]


def test_callback_facebook_crea_usuario_y_vincula_identidad(client, monkeypatch):
    def fake_llamar(metodo, url, **kwargs):
        if "oauth/access_token" in url:
            return {"access_token": "tok"}
        return {"id": "fb-100", "name": "Maria", "email": "maria@farmacia.test"}

    monkeypatch.setattr(oauth_service, "_llamar", fake_llamar)
    state = _state(client, "facebook")

    respuesta = client.get(f"/auth/facebook/callback?code=cod&state={state}")
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["usuario"]["rol"] == "empleado"
    assert datos["usuario"]["proveedores"] == ["facebook"]
    assert datos["usuario"]["email"] == "maria@farmacia.test"

    otra_vez = client.get(f"/auth/facebook/callback?code=cod&state={_state(client, 'facebook')}")
    assert otra_vez.get_json()["usuario"]["id_usuario"] == datos["usuario"]["id_usuario"]


def test_callback_instagram_via_facebook_login(client, monkeypatch):
    def fake_llamar(metodo, url, **kwargs):
        if "oauth/access_token" in url:
            return {"access_token": "tok-usuario"}
        if url.endswith("/me/accounts"):
            return {"data": [
                {"id": "pagina-1", "name": "Sin IG"},
                {"id": "pagina-2", "name": "Farmacia", "instagram_business_account": {"id": "ig-7"}},
            ]}
        return {"username": "farmacia_ig"}

    monkeypatch.setattr(oauth_service, "_llamar", fake_llamar)
    # Instagram agrega "#_" al código; va codificado en la URL para no tratarlo como fragmento.
    respuesta = client.get(f"/auth/instagram/callback?code=cod%23_&state={_state(client, 'instagram')}")
    assert respuesta.status_code == 200
    usuario = respuesta.get_json()["usuario"]
    assert usuario["nombre"] == "farmacia_ig"
    assert usuario["email"] is None
    assert usuario["proveedores"] == ["instagram"]


def test_instagram_sin_cuenta_profesional_vinculada(client, monkeypatch):
    def fake_llamar(metodo, url, **kwargs):
        if "oauth/access_token" in url:
            return {"access_token": "tok-usuario"}
        return {"data": [{"id": "pagina-1", "name": "Sin IG"}]}

    monkeypatch.setattr(oauth_service, "_llamar", fake_llamar)
    respuesta = client.get(f"/auth/instagram/callback?code=cod&state={_state(client, 'instagram')}")
    assert respuesta.status_code == 400
    assert "Página de Facebook" in respuesta.get_json()["mensaje"]


def test_google_no_vincula_correo_no_verificado(app):
    existente = usuario_service.registrar_local("Dueno", "dueno@farmacia.test", "clave-segura-1")

    nuevo = usuario_service.login_oauth("google", "g-1", "Otro", "dueno@farmacia.test", email_verificado=False)
    assert nuevo["id_usuario"] != existente["id_usuario"]

    vinculado = usuario_service.login_oauth("google", "g-2", "Dueno", "dueno@farmacia.test", email_verificado=True)
    assert vinculado["id_usuario"] == existente["id_usuario"]
    assert vinculado["proveedores"] == ["google"]


@pytest.mark.parametrize("proveedor", ["google", "facebook", "instagram"])
def test_state_de_un_proveedor_no_sirve_para_otro(client, proveedor):
    otro = "facebook" if proveedor != "facebook" else "google"
    state = _state(client, proveedor)
    respuesta = client.get(f"/auth/{otro}/callback?code=c&state={state}")
    assert respuesta.status_code == 400
