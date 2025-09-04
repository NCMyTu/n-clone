from src import DatabaseManager, DatabaseStatus
import pytest
from .utils import _sample_doujinshi


@pytest.fixture
def dbm():
	dbm = DatabaseManager(url=f"sqlite:///:memory:", test=True)
	dbm.logger.disable()
	status = dbm.create_database()
	assert status == DatabaseStatus.OK
	return dbm


@pytest.fixture
def sample_doujinshi():
	return _sample_doujinshi(1)