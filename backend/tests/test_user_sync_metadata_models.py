import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.models import AppUser, SourceConnection, SyncRun


def test_user_source_connection_and_sync_run_persist() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = AppUser(
            better_auth_user_id="better-auth-user-1",
            email="runner@example.com",
            display_name="Runner",
        )
        connection = SourceConnection(
            user=user,
            source="garmin",
            provider_subject_id="garmin-user-1",
            connection_metadata={"region": "gb"},
        )
        sync_run = SyncRun(
            user=user,
            source_connection=connection,
            status="succeeded",
            sync_type="manual",
            records_seen=3,
            records_imported=2,
        )

        session.add(sync_run)
        session.commit()

    with Session(engine) as session:
        persisted_user = session.scalar(
            select(AppUser).where(AppUser.better_auth_user_id == "better-auth-user-1")
        )
        assert persisted_user is not None
        assert isinstance(persisted_user.id, uuid.UUID)
        assert persisted_user.timezone == "UTC"
        assert persisted_user.source_connections[0].source == "garmin"
        assert persisted_user.source_connections[0].connection_metadata == {"region": "gb"}
        assert persisted_user.sync_runs[0].records_imported == 2


def test_user_sync_metadata_tables_define_expected_constraints() -> None:
    app_users = AppUser.__table__
    source_connections = SourceConnection.__table__
    sync_runs = SyncRun.__table__

    assert app_users.c.better_auth_user_id.nullable is False
    assert source_connections.c.user_id.foreign_keys
    assert sync_runs.c.user_id.foreign_keys
    assert sync_runs.c.source_connection_id.foreign_keys
    assert source_connections.c.metadata.nullable is False
    assert sync_runs.c.records_seen.nullable is False
    assert sync_runs.c.records_imported.nullable is False
