from sqlalchemy import Column, DateTime, Integer, String, Table

from app.database import Base


intento_oauth_web = Table(
    "intento_oauth_web",
    Base.metadata,
    Column("state_hash", String(64), primary_key=True),
    Column("desafio", String(43), nullable=False),
    Column("retorno", String(1024), nullable=False),
    Column("fase", String(12), nullable=False),
    Column("expira", DateTime, nullable=False),
    Column("codigo_hash", String(64)),
    Column("id_usuario", Integer),
)
