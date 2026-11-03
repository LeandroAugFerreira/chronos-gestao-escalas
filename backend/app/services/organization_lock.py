"""Serialização de escritas por organização para checagem e decisão atômicas."""
from sqlalchemy import update
from app.models.entities import Organization


def lock_organization(session, organization_id):
    # UPDATE inócuo adquire row lock no PostgreSQL e write lock no SQLite.
    session.execute(update(Organization).where(Organization.id == organization_id)
        .values(fixture_hash=Organization.fixture_hash).execution_options(synchronize_session=False))
