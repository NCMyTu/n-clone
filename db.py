# TODO: check which lazy option("selectin", "joined") in relationship
# 		has less select
# TODO: check insert_group log
from classes.database_new import DatabaseManager
from classes.models import Language
from sqlalchemy import create_engine, event, select

dbm = DatabaseManager("sqlite:///collection.db.sqlite", echo=False)

dbm.create_database()

dbm.insert_doujinshi(1, "full_name", "path_1")

dbm.insert_language("new_lang")

dbm.add_language_to_doujinshi(1, "new_lang")

d = dbm.get_doujinshi(1)

print("Languages:")
for lang in d.languages:
	print("\t", lang.name)