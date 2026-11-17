"""Agrega el almacenamiento de intentos OAuth Web."""
import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "intento_oauth_web",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("desafio", sa.String(43), nullable=False),
        sa.Column("retorno", sa.String(1024), nullable=False),
        sa.Column("fase", sa.String(12), nullable=False),
        sa.Column("expira", sa.DateTime(), nullable=False),
        sa.Column("codigo_hash", sa.String(64)),
        sa.Column("id_usuario", sa.Integer()),
    )
    op.create_index("ix_intento_oauth_web_expira", "intento_oauth_web", ["expira"])


def downgrade():
    op.drop_table("intento_oauth_web")
