from collections.abc import Generator

import pytest

from app.core.config import get_settings
from app.db.session import get_engine


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
