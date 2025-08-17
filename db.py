from classes.database_new import DatabaseManager
from classes.models import Language
from sqlalchemy import create_engine, event, select

db = DatabaseManager("sqlite:///collection.db.sqlite")

with db.session() as session:
	lang = Language(name="new language 1")
	# d = Doujinshi(id=3, full_name=" ", path="  ")
	session.add(lang)
	session.commit()

	statement = select(Language)
	langs = session.scalars(statement).all()
	for lang in langs:
		print(lang.name)