from src import DatabaseManager, DatabaseStatus
from sqlalchemy import text


def sample_doujinshi():
	return {
		"id": 177,
		"full_name": "This is a sample doujinshi",
		"pretty_name": "s is a sam",
		"full_name_original": "a",
		"pretty_name_original": "a",
		"path": "sample/path",
		"pages": ["f1.jpg", "f2.png"],
		"note": "This is a sample note",

		"parodies": ["this", "will", "be", "inserted", "then", "linked", "with", "the", "doujinshi"],
		"characters": ["same", "as", "above"],
		"tags": [], # This will trigger a warning.
		"artists": [], # Same as above.
		"groups": ["g_1"],
		"languages": ["english"]
	}


def print_doujinshi(doujinshi):
	print("-" * 25)
	for k, v in doujinshi.items():
		print(f"   {k}: {v}")
	print("-" * 25)


if __name__ == "__main__":
	dbm = DatabaseManager(url="sqlite:///:memory:", log_path="db.log", echo=False)

	dbm.create_database()
	# Optionally disable logging to avoid cluttering the output.
	# dbm.logger.disable()

	doujinshi = sample_doujinshi() # or load from json

	# ------ Insert a doujinshi ------
	dbm.insert_doujinshi(doujinshi)

	status, retrieved = dbm.get_doujinshi(doujinshi["id"])
	print("After insert:")
	print_doujinshi(retrieved)

	# ------ Insert another doujinshi ------
	doujinshi = sample_doujinshi()
	doujinshi["id"] += 1
	doujinshi["path"] = "new/path"
	doujinshi["characters"] = doujinshi["characters"][1:]
	dbm.insert_doujinshi(doujinshi)

	# ------ Update counts ------
	# dbm.update_count_of_all()

	status, retrieved = dbm.get_doujinshi(doujinshi["id"])
	print("After updating counts:")
	print_doujinshi(retrieved)

	# ------ Update doujinshi fields ------
	d_id = doujinshi["id"]

	dbm.update_full_name_of_doujinshi(d_id, "This is a new title")

	# ------ Add item to a doujinshi ------
	# To add an item to a doujinshi, it must exist first.
	# This is intentional to prevent any accidental misspelling or invalid name.
	new_parody = "new parody"
	dbm.insert_parody(new_parody)
	dbm.add_parody_to_doujinshi(d_id, new_parody)

	new_character = "THIS WILL BE CONVERTED TO LOWERCASE BEFORE BEING INSERTED"
	dbm.insert_character(new_character)
	# This will fail since the character is inserted in lowercase and added to doujinshi in uppercase.
	dbm.add_character_to_doujinshi(d_id, new_character)

	new_tag = ""
	# Empty string. This should "throw" a FATAL status.
	dbm.insert_tag(new_tag)
	dbm.add_tag_to_doujinshi(d_id, new_tag)

	# ------ Remove item from a doujinshi ------
	dbm.remove_parody_from_doujinshi(d_id, doujinshi["parodies"][0])

	# Again, remember to update count
	dbm.update_count_of_all()

	status, retrieved = dbm.get_doujinshi(d_id)
	print("After updates and removals:")
	print_doujinshi(retrieved)

	# ------ If you want to run raw SQL ------
	raw_sql = text("SELECT * FROM character")
	with dbm.session() as session:
		characters = session.execute(raw_sql).all()
		for character in characters:
			print(f"id: {character[0]}, name: {character[1]}, count: {character[2]}")