"""Create inventory items table."""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_items"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
    )
    op.create_index("ix_items_id", "items", ["id"])
    op.create_index("ix_items_sku", "items", ["sku"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_items_sku", table_name="items")
    op.drop_index("ix_items_id", table_name="items")
    op.drop_table("items")
