import pytest

from app.config import parsear_puertos


def test_varios_puertos():
    assert parsear_puertos("5000,5001") == [5000, 5001]


def test_espacios_y_comas_sobrantes():
    assert parsear_puertos(" 5000 , 5001, ") == [5000, 5001]


@pytest.mark.parametrize("texto", ["5000,5000", "0", "70000", "abc", " , "])
def test_puertos_invalidos(texto):
    with pytest.raises((RuntimeError, ValueError)):
        parsear_puertos(texto)


def test_config_usa_ports_y_respeta_port_singular(monkeypatch, settings):
    from app.config import Config

    monkeypatch.setenv("PORTS", "5000,5001")
    assert Config().ports == [5000, 5001]

    monkeypatch.delenv("PORTS")
    monkeypatch.setenv("PORT", "5002")
    assert Config().ports == [5002]
