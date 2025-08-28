from src import DatabaseManager, DatabaseStatus, extract_all_numbers as numerically
from src.models import Doujinshi, Parody, Character, Tag, Artist, Group, Language
from src.models import many_to_many_tables as m2m
import random
import time
from types import SimpleNamespace
from itertools import islice
from sqlalchemy import insert, text, select, func, inspect
from sqlalchemy.exc import IntegrityError


# {item_name: [id_in_db, count]}
PARODIES = {f"parody_{i}": [i, 0] for i in range(1, 10)}
CHARACTERS = {f"character_{i}": [i, 0] for i in range(1, 10)}
TAGS = {f"tag_{i}": [i, 0] for i in range(1, 50)}
ARTISTS = {f"artist_{i}": [i, 0] for i in range(1, 20)}
GROUPS = {f"group_{i}": [i, 0] for i in range(1, 5)}
LANGUAGES = {language: [i+1, 0] for i, language in enumerate(["english", "japanese", "textless", "chinese"])}


def pick_random_items(table):
	amount = random.randint(0, len(table))
	items = random.sample(list(table.keys()), amount)
	for item in items:
		table[item][1] += 1
	item_ids = [table[item][0] for item in items]
	return item_ids


def create_random_pages(p=0.85, mu_1=25, sigma_1=7, mu_2=200, sigma_2=50, lo=1, hi=250, random_state=2):
	if random.random() < p:
		n = int(random.gauss(mu_1, sigma_1))
	else:
		n = int(random.gauss(mu_2, sigma_2))

	n = max(lo, min(n, hi))
	return [f"page_{i}" for i in range(1, n+1)]


def generate_n_sample_doujinshis(
	n_doujinshis,
	parodies=PARODIES,
	characters=CHARACTERS,
	tags=TAGS,
	artists=ARTISTS,
	groups=GROUPS,
	languages=LANGUAGES,
	random_state=2
):
	random.seed(random_state)

	for i in range(1, n_doujinshis + 1):
		yield {
			"id": i,
			"full_name": "Test Doujinshi",
			"pretty_name": "st Dou",
			"full_name_original": "元の名前",
			"pretty_name_original": "の名",
			"path": f"path/{i}",
			"note": "Test note",
			"parodies": pick_random_items(PARODIES),
			"characters": pick_random_items(CHARACTERS),
			"tags": pick_random_items(TAGS),
			"artists": pick_random_items(ARTISTS),
			"groups": pick_random_items(GROUPS),
			"languages": pick_random_items(LANGUAGES),
			"pages": create_random_pages()
		}


def batch_insert_doujinshi(dbm, d_generator, batch_size):
	total_time = 0
	n_doujinshis = 0

	while True:
		d_batch = list(islice(d_generator, batch_size))
		if not d_batch:
			break

		mapping = {
			"parodies": ["parodies_to_insert", "parody_id", PARODIES],
			"characters": ["characters_to_insert", "character_id", CHARACTERS],
			"tags": ["tags_to_insert", "tag_id", TAGS],
			"artists": ["artists_to_insert", "artist_id", ARTISTS],
			"groups": ["groups_to_insert", "circle_id", GROUPS],
			"languages": ["languages_to_insert", "language_id", LANGUAGES],
		}
		doujinshis_to_insert = []
		items_to_insert = {item[0]: [] for item in mapping.values()}

		for doujinshi in d_batch:
			doujinshis_to_insert.append({
					"id": doujinshi["id"],
					"full_name": doujinshi["full_name"],
					"pretty_name": doujinshi["pretty_name"],
					"full_name_original": doujinshi["full_name_original"],
					"pretty_name_original": doujinshi["pretty_name_original"],
					"path": doujinshi["path"],
					"note": doujinshi["note"]
			})

			for item_type, value in mapping.items():
				value_to_insert = value[0]
				value_id = value[1]
				for item_id in doujinshi[item_type]:
					items_to_insert[value_to_insert].append({
						"doujinshi_id": doujinshi["id"],
						value_id: item_id
					})

		start = time.perf_counter()
		with dbm.session() as session:
			try:
				session.execute(insert(Doujinshi), doujinshis_to_insert)

				session.execute(insert(m2m.doujinshi_parody), items_to_insert["parodies_to_insert"])
				session.execute(insert(m2m.doujinshi_character), items_to_insert["characters_to_insert"])
				session.execute(insert(m2m.doujinshi_tag), items_to_insert["tags_to_insert"])
				session.execute(insert(m2m.doujinshi_artist), items_to_insert["artists_to_insert"])
				session.execute(insert(m2m.doujinshi_circle), items_to_insert["groups_to_insert"])
				session.execute(insert(m2m.doujinshi_language), items_to_insert["languages_to_insert"])

				session.commit()
			except IntegrityError:
				session.rollback()
				continue # to continue generate batches
			except Exception:
				raise
		elapsed = time.perf_counter() - start
		print(f"Inserting {d_batch[-1]['id']} doujinshi took {elapsed:.2f}s.")

		total_time += elapsed
		n_doujinshis = d_batch[-1]["id"]

	print(f"Inserting {n_doujinshis} doujinshi took a total of {total_time:.2f}s.")


def batch_insert_model(dbm, model, data):
	items_to_insert = [{"name": parody} for parody in data]

	with dbm.session() as session:
		try:
			session.execute(insert(model), items_to_insert)
			session.commit()
		except IntegrityError:
			raise
		except Exception:
			raise


if __name__ == "__main__":
	insert_batch_size = 30_000
	d_gen = generate_n_sample_doujinshis(1_000_000)

	dbm = DatabaseManager(url=f"sqlite:///tests/db/1M_rowid.db.sqlite", log_path="tests/db/1M_rowid.log", echo=False)
	dbm.logger.disable()
	dbm.create_database()

	# try:
	# 	batch_insert_model(dbm, Parody, PARODIES)
	# 	batch_insert_model(dbm, Character, CHARACTERS)
	# 	batch_insert_model(dbm, Tag, TAGS)
	# 	batch_insert_model(dbm, Artist, ARTISTS)
	# 	batch_insert_model(dbm, Group, GROUPS)
	# except IntegrityError:
	# 	print("Database exists. Continue...")
	# except Exception as e:
	# 	raise ValueError(f"Unexpected exception when inserting model.\n{e}")
	
	# try:
	# 	batch_insert_doujinshi(dbm, d_gen, insert_batch_size)
	# except IntegrityError:
	# 	print("Database exists. Continue...")
	# except Exception as e:
	# 	raise ValueError(f"Unexpected exception when inserting doujinshi.\n{e}")

	# start = time.perf_counter()
	# dbm.update_count_of_all()
	# print("Update all count took ", time.perf_counter() - start)

	with dbm.session() as session:
		for i in range(10):
			start = time.perf_counter()
			return_status, db_count = dbm.get_count_of_languages(list(LANGUAGES.keys()))
			print("no index, ", time.perf_counter() - start, db_count)



		print("LANGUAGES: ", LANGUAGES)

		statement = text("PRAGMA index_list('doujinshi_language');")
		count = session.execute(statement).all()
		print("\n", count)