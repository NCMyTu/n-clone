import pytest
from src import DatabaseStatus


def test_remove_doujinshi(dbm, sample_doujinshi):
	assert dbm.insert_doujinshi(sample_doujinshi, False) == DatabaseStatus.OK

	assert dbm.remove_doujinshi(sample_doujinshi["id"]) == DatabaseStatus.OK
	assert dbm.remove_doujinshi(sample_doujinshi["id"]) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND
	assert dbm.remove_doujinshi(-9999999) == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND