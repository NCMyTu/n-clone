# TODO: check which lazy option("selectin", "joined") in relationship
# 		has less select
# TODO: check insert_group log
from classes.database_new import DatabaseManager
from classes.models import Language
from sqlalchemy import create_engine, event, select

dbm = DatabaseManager("sqlite:///collection.db.sqlite", echo=False)

dbm.insert_parody("new_parody3")