import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import (
    Activity,
    AppUser,
    BiometricSample,
    DailyMetric,
    RawObservation,
    SleepSession,
    SourceConnection,
    SyncRun,
)
from app.services.demo_data import DemoDataService


@pytest.mark.anyio
async def test_demo_data_service_creates_and_refreshes_user_scoped_records() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db.models import Base

    Base.metadata.create_all(engine)
    db = Session(engine)
    user = AppUser(
        better_auth_user_id="demo-service-user",
        email="demo-service@example.test",
        display_name="Demo Service User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        service = DemoDataService()
        first_sync = await service.load_dashboard_data(db, user)
        second_sync = await service.load_dashboard_data(db, user)

        source_connection = db.scalar(select(SourceConnection))
        assert first_sync.status == "succeeded"
        assert second_sync.status == "succeeded"
        assert source_connection is not None
        assert source_connection.source == "demo"
        assert source_connection.connection_metadata["credentials_required"] is False
        assert db.scalar(select(func.count(Activity.id))) > 0
        assert db.scalar(select(func.count(DailyMetric.id))) == 14
        assert db.scalar(select(func.count(SleepSession.id))) == 14
        assert db.scalar(select(func.count(BiometricSample.id))) == 14
        assert db.scalar(select(func.count(RawObservation.id))) == first_sync.records_seen
        assert db.scalar(select(func.count(SyncRun.id))) == 2
    finally:
        db.close()
