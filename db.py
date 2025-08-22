# TODO: check which lazy option("selectin", "joined") in relationship
# 		has less select
# TODO: check insert_group log
from src.database import DatabaseManager
from src.models import Language, Doujinshi
from sqlalchemy import create_engine, event, select
from src import utils
from types import SimpleNamespace


dbm = DatabaseManager("sqlite:///collection.db.sqlite", echo=False)

dbm.create_database()
dbm.insert_parody("p_2")
dbm.insert_parody("p_3")
dbm.insert_parody("p_1")

doujinshi = {
	"id": 4,
	"full_name": "full_name",
	"full_name_original": "",
	"pretty_name": "",
	"pretty_name_original": "",
	"path": "path_4",
	"pages": ["f1.jpg", "f2.png"],
	"note": "",

	"parodies": ["p_1", "p_2", "bb"],
	"characters": [],
	"tags": [],
	"artists": [],
	"groups": [],
	"languages": []
}
dbm.insert_doujinshi(doujinshi, True)

doujinshi = {
	"id": 5,
	"full_name": "full_name",
	"full_name_original": "",
	"pretty_name": "",
	"pretty_name_original": "",
	"path": "path_5",
	"pages": ["f1.jpg", "f2.png"],
	"note": "",

	"parodies": ["p_1", "p_2", "bb", "p_3"],
	"characters": [],
	"tags": [],
	"artists": [],
	"groups": [],
	"languages": []
}
dbm.insert_doujinshi(doujinshi, True)

# dbm.add_parody_to_doujinshi(4, "p_3")
dbm.add_pages_to_doujinshi(4, doujinshi["pages"])
dbm.remove_parody_from_doujinshi(4, "bb")
# dbm.remove_doujinshi(4)
dbm.update_path_of_doujinshi(5, "path_4")

ret_status, d = dbm.get_doujinshi(5)
print(d)

# parodies_to_query = doujinshi["parodies"] + ["should_be_0"]

# count_dict = dbm.get_count_of_parodies(parodies_to_query)
# print(count_dict)