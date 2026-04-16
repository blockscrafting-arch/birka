"""Merge two migration heads into one.

Revision ID: 0031_merge_heads
Revises: 0007_fbo_external_ids, 0030_cascade_order_photo_packing
"""
revision = "0031_merge_heads"
down_revision = ("0007_fbo_external_ids", "0030_cascade_order_photo_packing")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
