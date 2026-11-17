"""Garantiza la unicidad de cédula y correo de empleados."""
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        SET ANSI_NULLS ON;
        SET ANSI_PADDING ON;
        SET ANSI_WARNINGS ON;
        SET ARITHABORT ON;
        SET CONCAT_NULL_YIELDS_NULL ON;
        SET QUOTED_IDENTIFIER ON;
        SET NUMERIC_ROUNDABORT OFF;
    """)
    for campo in ("cedula", "correo"):
        filtro = "" if campo == "cedula" else " WHERE [correo] IS NOT NULL"
        filtro_existente = "i.has_filter = 0"
        if campo == "correo":
            filtro_existente += """ OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                i.filter_definition, '[', ''), ']', ''), '(', ''), ')', ''), ' ', '')) = 'correoisnotnull'"""
        op.execute(f"""
            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes AS i
                JOIN sys.index_columns AS k
                    ON k.object_id = i.object_id AND k.index_id = i.index_id AND k.key_ordinal = 1
                JOIN sys.columns AS c ON c.object_id = k.object_id AND c.column_id = k.column_id
                WHERE i.object_id = OBJECT_ID(N'dbo.Empleado', N'U')
                  AND i.is_unique = 1 AND i.is_disabled = 0 AND i.is_hypothetical = 0
                  AND i.ignore_dup_key = 0 AND c.name = N'{campo}'
                  AND ({filtro_existente})
                  AND NOT EXISTS (
                      SELECT 1 FROM sys.index_columns AS otro
                      WHERE otro.object_id = i.object_id AND otro.index_id = i.index_id
                        AND otro.key_ordinal > 1
                  )
            )
                CREATE UNIQUE INDEX [UX_Empleado_{campo}_0004]
                ON [dbo].[Empleado] ([{campo}]){filtro};
        """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS [UX_Empleado_correo_0004] ON [dbo].[Empleado];")
    op.execute("DROP INDEX IF EXISTS [UX_Empleado_cedula_0004] ON [dbo].[Empleado];")
