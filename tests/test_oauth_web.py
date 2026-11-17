import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from app.services import oauth_service


RETORNO = "http://localhost:58819/"
VERIFICADOR = "v" * 43
DESAFIO = base64.urlsafe_b64encode(hashlib.sha256(VERIFICADOR.encode()).digest()).decode().rstrip("=")


def _iniciar(client):
    respuesta = client.get("/auth/google/login", query_string={"retorno": RETORNO, "desafio": DESAFIO})
    assert respuesta.status_code == 200, respuesta.get_json()
    cuerpo = respuesta.get_json()
    params = parse_qs(urlparse(cuerpo["authorization_url"]).query)
    assert params["redirect_uri"] == ["http://api.test/auth/google/callback"]
    assert params["state"] == [cuerpo["state"]]
    return cuerpo["state"]


def test_oauth_web_entrega_codigo_y_solo_la_pestana_correcta_puede_canjearlo(client, settings, monkeypatch):
    settings.oauth_frontend_returns = {RETORNO}

    def proveedor(metodo, url, **kwargs):
        if url.endswith("/token"):
            return {"access_token": "token-del-proveedor"}
        return {"sub": "google-web", "name": "Ana", "email": "ana@ejemplo.test", "email_verified": True}

    monkeypatch.setattr(oauth_service, "_llamar", proveedor)
    state = _iniciar(client)
    datos_callback = {"state": state, "code": "codigo-del-proveedor"}
    callback = client.get("/auth/google/callback", query_string=datos_callback)
    assert callback.status_code == 303
    assert callback.headers["Cache-Control"] == "no-store"
    destino = urlparse(callback.location)
    assert destino.netloc == "localhost:58819"
    parametros = parse_qs(destino.query)
    assert set(parametros) == {"oauth_code", "oauth_state"}
    assert parametros["oauth_state"] == [state]

    solicitud = {"state": state, "code": parametros["oauth_code"][0], "verifier": VERIFICADOR}
    assert client.post("/auth/intercambiar", json={**solicitud, "verifier": "x" * 43}).status_code == 400
    canje = client.post("/auth/intercambiar", json=solicitud)
    assert canje.status_code == 200
    assert canje.headers["Cache-Control"] == "no-store"
    token = canje.get_json()["access_token"]
    perfil = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert perfil.status_code == 200
    assert perfil.get_json()["rol"] == "empleado"
    assert client.post("/auth/intercambiar", json=solicitud).status_code == 400
    assert client.get("/auth/google/callback", query_string=datos_callback).status_code == 400


def test_oauth_web_rechaza_retorno_fuera_de_lista_y_comunica_cancelacion(client, settings):
    settings.oauth_frontend_returns = {RETORNO}
    externo = client.get("/auth/google/login", query_string={"retorno": "https://externo.test/", "desafio": DESAFIO})
    assert externo.status_code == 400
    state = _iniciar(client)
    respuesta = client.get("/auth/google/callback", query_string={"state": state, "error": "access_denied"})
    assert respuesta.status_code == 303
    parametros = parse_qs(urlparse(respuesta.location).query)
    assert parametros == {"oauth_state": [state], "oauth_error": ["cancelado"]}
