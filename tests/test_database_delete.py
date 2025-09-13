import pytest
from src import DatabaseStatus
import random


def test_remove_doujinshi(dbm, sample_n_random_doujinshi):
	doujinshi_list, _ = sample_n_random_doujinshi(50)

	assert dbm.remove_doujinshi(-999) == DatabaseStatus.NOT_FOUND
	assert dbm.remove_doujinshi(10**9) == DatabaseStatus.NOT_FOUND

	for doujinshi in doujinshi_list:
		dbm.insert_doujinshi(doujinshi)

	random.shuffle(doujinshi_list)
	for doujinshi in doujinshi_list:
		assert dbm.remove_doujinshi(doujinshi["id"]) == DatabaseStatus.OK

	random.shuffle(doujinshi_list)
	for doujinshi in doujinshi_list:
		assert dbm.remove_doujinshi(doujinshi["id"]) == DatabaseStatus.NOT_FOUND

	assert dbm.remove_doujinshi(-999) == DatabaseStatus.NOT_FOUND
	assert dbm.remove_doujinshi(10**9) == DatabaseStatus.NOT_FOUND