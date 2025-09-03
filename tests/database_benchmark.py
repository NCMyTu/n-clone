from src import DatabaseManager, DatabaseStatus, extract_all_numbers as numerically
from src.models import Doujinshi, Parody, Character, Tag, Artist, Group, Language, Page
from src.models import many_to_many_tables as m2m
import random
import time
from types import SimpleNamespace
from itertools import islice
from sqlalchemy import insert, text, select, func, inspect
from sqlalchemy.exc import IntegrityError
from pathlib import Path
import numpy as np


# {item_name: [id_in_db, count]}
PARODIES = {f"parody_{i}": [i, 0] for i in range(1, 500)}
CHARACTERS = {f"character_{i}": [i, 0] for i in range(1, 500)}
TAGS = {f"tag_{i}": [i, 0] for i in range(1, 500)}
ARTISTS = {f"artist_{i}": [i, 0] for i in range(1, 500)}
GROUPS = {f"group_{i}": [i, 0] for i in range(1, 500)}
LANGUAGES = {language: [i+1, 0] for i, language in enumerate(["english", "japanese", "textless", "chinese"])}


def time_func(func, n=1, *args, **kwargs):
	durations = []
	result = None

	for _ in range(n):
		start = time.perf_counter()
		result = func(*args, **kwargs)
		durations.append(time.perf_counter() - start)

	return result, durations


def convert_to_ms(durations):
	return [d * 1000 for d in durations]


def get_stats(durations):
	return {
		"avg": sum(durations) / len(durations),
		"p50": np.percentile(durations, 50),
		"p95": np.percentile(durations, 95),
		"p99": np.percentile(durations, 99)
	}


def get_row_count(dbm):
	tbl_names = [
		"doujinshi_parody", "doujinshi_character", "doujinshi_tag", 
		"doujinshi_artist", "doujinshi_circle", "doujinshi_language", 
		"page", "total"
	]
	row_count = {tbl: 0 for tbl in tbl_names}
	with dbm.session() as session:
		for tbl_name in tbl_names[:-1]:
			row_count[tbl_name] = session.scalar(text(f"SELECT COUNT(*) FROM {tbl_name}"))
			row_count["total"] += row_count[tbl_name]
	return row_count


def pick_random_items(table, type):
	if type == "tag":
		base_min, base_max = 0, 15
		rare_max = 100
	elif type == "character":
		base_min, base_max = 0, 4
		rare_max = 20
	elif type == "parody":
		base_min, base_max = 0, 2
		rare_max = 10
	elif type == "artist":
		base_min, base_max = 0, 2
		rare_max = 30
	elif type == "group":
		base_min, base_max = 0, 1
		rare_max = 3
	elif type == "language":
		base_min, base_max = 1, 1
		rare_max = 2

	if random.random() < 0.97:
		amount = random.randint(base_min, min(base_max, len(table)))
	else: # mythical pull
		amount = random.randint(rare_max, len(table))

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
			"full_name": "Test",
			"pretty_name": "e",
			"full_name_original": "ts",
			"pretty_name_original": "t",
			"path": f"p{i}",
			"note": "note",
			"parodies": pick_random_items(PARODIES, "parody"),
			"characters": pick_random_items(CHARACTERS, "character"),
			"tags": pick_random_items(TAGS, "tag"),
			"artists": pick_random_items(ARTISTS, "artist"),
			"groups": pick_random_items(GROUPS, "group"),
			"languages": pick_random_items(LANGUAGES, "language"),
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
		pages_to_insert = []

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

			for order_number, page in enumerate(doujinshi["pages"], start=1):
				pages_to_insert.append({
					"filename": page,
					"order_number": order_number,
					"doujinshi_id": doujinshi["id"]
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

				session.execute(insert(Page), pages_to_insert)

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


def _benchmark_get_doujinshi_predictable(dbm, id_start, step, n_times):
	durations = []
	for doujinshi_id in range(id_start, id_start + step * n_times, step):
		start = time.perf_counter()
		dbm.get_doujinshi(doujinshi_id)
		durations.append(time.perf_counter() - start)
	return convert_to_ms(durations)


def _benchmark_get_doujinshi_random(dbm, id_min, id_max, n_times, random_state=2):
	random.seed(random_state)
	durations = []
	for _ in range(n_times):
		doujinshi_id = random.randint(id_min, id_max)
		start = time.perf_counter()
		dbm.get_doujinshi(doujinshi_id)
		durations.append(time.perf_counter() - start)
	return convert_to_ms(durations)


def benchmark_get_doujinshi(dbm, n_times, mode):
	warmup_id_range = [int(i * 1_000_000 / 19) for i in range(20)]
	warmup_id_range[0] = 1
	for doujinshi_id in warmup_id_range:
		dbm.get_doujinshi(doujinshi_id)
	print(f"Warmed up for {len(warmup_id_range)} rounds.")

	if mode == "predictable":
		print("-----Predictable access-----")
		durations = []
		for doujinshi_id, step in [(3_000, 2), (499_799, 4), (975_172, 7)]:
			_durations = _benchmark_get_doujinshi_predictable(dbm, doujinshi_id, step, n_times)
			stats = get_stats(_durations)
			print(f"id: {doujinshi_id}, step: {step}, avg: {stats['avg']:.2f}ms, p50: {stats['p50']:.2f}ms, p95: {stats['p95']:.2f}ms, p99: {stats['p99']:.2f}ms")
			durations.extend(_durations)
		stats = get_stats(durations)
		print(f"Overall, avg: {stats['avg']:.2f}ms, p50: {stats['p50']:.2f}ms, p95: {stats['p95']:.2f}ms, p99: {stats['p99']:.2f}ms")

	if mode == "random":
		print("-----Random access-----")
		durations = []
		for id_range in [(100, 50_000), (470_011, 610_010), (700_001, 1_000_000)]:
			_durations = _benchmark_get_doujinshi_random(dbm, id_range[0], id_range[1], n_times)
			stats = get_stats(_durations)
			print(f"range: {id_range[0]}–{id_range[1]}, avg: {stats['avg']:.2f}ms, p50: {stats['p50']:.2f}ms, p95: {stats['p95']:.2f}ms, p99: {stats['p99']:.2f}ms")
			durations.extend(_durations)
		stats = get_stats(durations)
		print(f"Overall, avg: {stats['avg']:.2f}ms, p50: {stats['p50']:.2f}ms, p95: {stats['p95']:.2f}ms, p99: {stats['p99']:.2f}ms")


def benchmark_insert_doujinshi(dbm, n_doujinshis):
	random.seed(5)

	row_count_before = get_row_count(dbm)

	ID_TO_PARODY = {v[0]: k for k, v in PARODIES.items()}
	ID_TO_CHARACTER = {v[0]: k for k, v in CHARACTERS.items()}
	ID_TO_TAG = {v[0]: k for k, v in TAGS.items()}
	ID_TO_ARTIST = {v[0]: k for k, v in ARTISTS.items()}
	ID_TO_GROUP = {v[0]: k for k, v in GROUPS.items()}
	ID_TO_LANGUAGE = {v[0]: k for k, v in LANGUAGES.items()}

	doujinshis = list(generate_n_sample_doujinshis(n_doujinshis))
	for i, doujinshi in enumerate(doujinshis):
		doujinshi["id"] = 1_000_000 + i + 1
		doujinshi["path"] = f"path/{doujinshi["id"]}"
		
		# Evil long lines
		doujinshi["parodies"] = [ID_TO_PARODY[_id] for _id in doujinshi["parodies"]] or [random.choice(list(ID_TO_PARODY.values()))]
		doujinshi["characters"] = [ID_TO_CHARACTER[_id] for _id in doujinshi["characters"]] or [random.choice(list(ID_TO_CHARACTER.values()))]
		doujinshi["tags"] = [ID_TO_TAG[_id] for _id in doujinshi["tags"]] or [random.choice(list(ID_TO_TAG.values()))]
		doujinshi["artists"] = [ID_TO_ARTIST[_id] for _id in doujinshi["artists"]] or [random.choice(list(ID_TO_ARTIST.values()))]
		doujinshi["groups"] = [ID_TO_GROUP[_id] for _id in doujinshi["groups"]] or [random.choice(list(ID_TO_GROUP.values()))]
		doujinshi["languages"] = [ID_TO_LANGUAGE[_id] for _id in doujinshi["languages"]] or [random.choice(list(ID_TO_LANGUAGE.values()))]

	durations = []
	for doujinshi in doujinshis:
		start = time.perf_counter()
		dbm.insert_doujinshi(doujinshi, False)
		durations.append(time.perf_counter() - start)

	stats = get_stats(convert_to_ms(durations))

	print("-" * 30)
	print("Benchmarking dbm.insert_doujinshi()...")
	print(f"avg: {stats['avg']:.2f}ms, p50: {stats['p50']:.2f}ms, p95: {stats['p95']:.2f}ms, p99: {stats['p99']:.2f}ms")
	print("-" * 30)

	with dbm.session() as session:
		session.execute(text("PRAGMA foreign_keys = ON"))
		session.execute(text("DELETE FROM doujinshi WHERE id > 1000000"))
		session.commit()

	row_count_after = get_row_count(dbm)
	if row_count_before != row_count_after:
		raise ValueError("WARNING: ORPHAN ITEMS.")


def benchmark_get_doujinshi_in_page(dbm, n_pages):
	random.seed(2)
	page_size = 25
	max_pages = 1_000_000 // page_size

	start_end_point = [
		(1, n_pages + 1),
		((max_pages // 2) - (n_pages // 2), (max_pages // 2) - (n_pages // 2) + n_pages),
		(max_pages - n_pages, max_pages)
	]

	page_ranges = []
	for start, end in start_end_point:
		page_range = list(range(start, end))
		random.shuffle(page_range)
		page_ranges.append(page_range)

	print("Benchmarking dbm.get_doujinshi_in_page()...")

	for (page_start, page_end), page_range in zip(start_end_point, page_ranges):
		durations = []

		for i, page_number in enumerate(page_range):
			start_time = time.perf_counter()
			_, doujinshi_batch = dbm.get_doujinshi_in_page(page_size, page_number, 1000000)
			durations.append(time.perf_counter() - start_time)

		stats = get_stats(convert_to_ms(durations))
		print(f"pages {page_start} - {page_end}, avg: {stats['avg']:.2f}ms, ", end="")
		print(f"p50: {stats['p50']:.2f}ms, p95: {stats['p95']:.2f}ms, p99: {stats['p99']:.2f}ms")


if __name__ == "__main__":
	insert_batch_size = 10_000
	n_doujinshis = 1_000_000
	with_rowid_path = "tests/db/1M_rowid.db.sqlite"
	without_rowid_path = "tests/db/1M_without_rowid.db.sqlite"

	db_path = without_rowid_path
	print(db_path, "\n", "-" * 30)

	dbm = DatabaseManager(url=f"sqlite:///{db_path}", log_path="tests/db/1M.log", echo=False)
	dbm.logger.disable()
	dbm.create_database()

	# dbm.drop_index()
	# dbm.create_index()
	dbm.show_index()

	print("-" * 30)

	# ----------------------------
	# Only run this when inserting.
	# with dbm.session() as session:
	# 	session.execute(text("PRAGMA synchronous = OFF;"))
	# 	session.execute(text("PRAGMA journal_mode = MEMORY;"))
	# 	session.execute(text("PRAGMA temp_store = MEMORY;"))
	# 	session.commit()

	# Insert these first...
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

	# ...then this.
	# try:
	# 	d_gen = generate_n_sample_doujinshis(n_doujinshis)
	# 	batch_insert_doujinshi(dbm, d_gen, insert_batch_size)
	# except IntegrityError:
	# 	print("Database exists. Continue...")
	# except Exception as e:
	# 	raise ValueError(f"Unexpected exception when inserting doujinshi.\n{e}")

	# ----------------------------
	# Only need to run this after inserting or creating/dropping index.
	# with dbm.session() as session:
	# 	session.execute(text("VACUUM"))
	
	# ----------------------------
	# _, durations = time_func(dbm.update_count_of_all, n=10)
	# print(durations)
	# print(f"min: {min(durations):.2f}, max: {max(durations):.2f}, avg: {sum(durations)/len(durations):.2f}")

	# ----------------------------
	# for db_type in [with_rowid_path, without_rowid_path]:
	# 	size = Path(db_type).stat().st_size
	# 	print(f"{db_type}: {size / (1024**3):.4f}GB")

	# ----------------------------
	# benchmark_get_doujinshi(dbm, 1_000, "predictable")
	# benchmark_get_doujinshi(dbm, 1_000, "random")

	# ----------------------------
	benchmark_get_doujinshi_in_page(dbm, n_pages=500)

	# ----------------------------
	# benchmark_insert_doujinshi(dbm, 1000)