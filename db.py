# TODO: check which lazy option("selectin", "joined") in relationship
# 		has less select
# TODO: check insert_group log
from src.database_new import DatabaseManager
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

d = dbm.get_doujinshi(4) # should return status code as well
print("parodies: ", ", ".join([p.name for p in d.parodies]))

d = dbm.remove_doujinshi(3)

d = dbm.get_doujinshi(4)
print("parodies: ", ", ".join([p.name for p in d.parodies]))

parodies_to_query = doujinshi["parodies"] + ["should_be_0"]

count_dict = dbm.get_count_of_parodies(parodies_to_query)
print(count_dict)

count_dict = dbm.get_count_of(parodies=parodies_to_query)
print(count_dict)