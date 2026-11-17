from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos y por Alembic."""


_engine = None
_SessionLocal = None


def inicializar(database_url):
    global _engine, _SessionLocal
    _engine = create_engine(database_url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def engine():
    if _engine is None:
        raise RuntimeError("La base de datos no ha sido inicializada")
    return _engine


def sesion():
    if _SessionLocal is None:
        raise RuntimeError("La base de datos no ha sido inicializada")
    return _SessionLocal()
