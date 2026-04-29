"""Initial migration

Revision ID: 2b988e1078ca
Revises: 
Create Date: 2026-03-16 12:30:43.724240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b988e1078ca'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('vacancies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('company', sa.String(length=255), nullable=False),
    sa.Column('url', sa.String(length=512), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('salary', sa.String(length=100), nullable=True),
    sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('technologies', sa.JSON(), nullable=False),
    sa.Column('ai_summary', sa.Text(), nullable=True),
    sa.Column('suitability_score', sa.Integer(), nullable=True),
    sa.Column('is_analyzed', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vacancies_url'), 'vacancies', ['url'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_vacancies_url'), table_name='vacancies')
    op.drop_table('vacancies')