from src import DatabaseManager, DatabaseStatus
import pytest
from .utils import _sample_n_random_doujinshi
from pathlib import Path


@pytest.fixture
def dbm():
	log_path = Path("tests/db_test.log")
	# log_path.unlink(missing_ok=True)
	dbm = DatabaseManager(url=f"sqlite:///:memory:", log_path=log_path.as_posix(),test=True)
	dbm.disable_logger()
	status = dbm.create_database()
	assert status == DatabaseStatus.OK
	return dbm


@pytest.fixture
def sample_doujinshi():
	doujinshi_list, _ = _sample_n_random_doujinshi(1)
	return doujinshi_list[0]


@pytest.fixture
def sample_n_random_doujinshi():
	# return doujishi_list and its item_counts
	return _sample_n_random_doujinshi