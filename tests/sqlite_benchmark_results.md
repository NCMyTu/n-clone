# SQLite Benchmark Results
Summarize database performance benchmarks. As the title suggests, this is specific to SQLite. Benchmark again when you change the underlying database.

---

## Some definitions
* Doujinshi: You know.
* Item type: One of these: `Parody`, `Character`, `Tag`, `Artist`, `Group`, `Language`, `Page`.
* Item: An instance of an item type.
* Extra index: A manually created index (`{item_type_id}, doujinshi_id`) on many-to-many table (`doujinshi_{item_type}`) as opposed to the automatically created index (`doujinshi_id, {item_type_id}`).
* **Note**: the underlying name of `Group` is `circle` to avoid reserved keyword in SQLite.

---

## 1. Insert doujinshi
* Insert 1,000,000 randomly generated (with fixed seed) doujinshi in batches of 10,000.
* Number of items by type:  
  * `Parody`, `Tag`, `Character`, `Artist`, and `Group`: 500 items each.
  * `Language`: 4 items.
  * `Page`: up to 250 items per doujinshi.
* Item distribution by type:  
  * Each item type (except `Page`) has a 97% chance to sample without replacement a random number of items from **base_min** up to **base_max**, and a 3% chance to sample without replacement a random number of items from **rare_max** up to the total number of items.
  * `Page` has an 85% chance to sample the number of pages from a Gaussian distribution with mean 25 and stddev 7, and a 15% chance to sample from a Gaussian distribution with mean 200 and stddev 50. The number of pages is clamped between 1 and 250.

| Item type | base_min | base_max | rare_max |
|-----------|---------:|---------:|---------:|
| Parody    | 0 | 2  | 10  |
| Character | 0 | 4  | 20  |
| Tag       | 0 | 15 | 100 |
| Artist    | 0 | 2  | 30  |
| Group     | 0 | 1  | 3   |
| Language  | 1 | 1  | 2   |

* Results:
  * **Note**: Doujinshi and items are inserted directly into the database using IDs (so no duplicate or violation checks are performed). Therefore, insert time is faster than when using the actual insert method provided by `DatabaseManager`, which will be slower due to validation overhead.
  * Insert time is not shown for configurations with an extra index, since indexes can just be created after insertion ~~(definitely not because i don't have the patience to wait another 1000+ minutes)~~.

| Configuration                 | File size | Insert time (s) |
|-------------------------------|----------:|--------:|
| With ROWID, no extra index    | 4.9111 GB | 1099.15 |
| With ROWID, extra index       | 5.6435 GB |         |
| Without ROWID, no extra index | 2.7552 GB | 1046.06 |
| Without ROWID, extra index    | 3.2811 GB |         |

* Number of rows inserted:

| Table               |       Rows |
|---------------------|-----------:|
| doujinshi_parody    | 8,554,800  |
| doujinshi_character | 9,813,695  |
| doujinshi_tag       | 16,264,622 |
| doujinshi_artist    | 8,994,647  |
| doujinshi_circle    | 8,029,873  |
| doujinshi_language  | 1,060,181  |
| page                | 50,089,160 |
| **Total**           | **102,157,978** |

---

## 2. Update All Counts
* Mesure in **seconds** how long it takes to count how many doujinshi each item type has.
* Run `n_times` times.
* Results:

| Configuration                 | n_times | min | max | avg |
|-------------------------------|--------:|----:|----:|----:|
| With ROWID, no extra index    | 10  | 18.48 | 19.89 | 19.50 |
| With ROWID, extra index       | 100 | 3.02  | 3.73  | 3.18  |
| Without ROWID, no extra index | 10  | 16.55 | 20.44 | 18.25 |
| Without ROWID, extra index    | 100 | 2.67  | 6.60  | 3.05  |

---

## 3. Get Doujinshi
* Measure in **microseconds** how long it takes to get info of 1 doujinshi from database.
* Report metrics: average (`avg`), 95th percentile (`p95`), 99th percentile (`p99`).
* Each run has a warm-up: fetch 20 doujinshi at evenly spaced IDs from 1 to 1,000,000, then run Predictable Access and Random Access in that order. The results below are sorted for clarity, not shown in the exact order the benchmark runs.

### Predictable access
* Fetch 500 doujinshi starting from `id_start`, with step size `step`.
* Results:

| Configuration | id_start | step | avg | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| With ROWID, no extra index | 17,000 | 2 | 6.57 | 10.13 | 14.11 |
|  | 510,001 | 5 | 6.52 | 9.70 | 12.63 |
|  | 987,172 | 7 | 6.60 | 10.31 | 13.38 |
|  |  | **Overall** | **6.56** | **10.06** | **13.28** |
| With ROWID, extra index | 17,000 | 2 | 6.56 | 10.26 | 14.48 |
|  | 510,001 | 5 | 6.50 | 9.78 | 13.04 |
|  | 987,172 | 7 | 6.59 | 10.25 | 13.75 |
|  |  | **Overall** | **6.55** | **10.16** | **13.92** |
| Without ROWID, no extra index | 17,000 | 2 | 7.21 | 11.28 | 15.09 |
|  | 510,001 | 5 | 7.01 | 10.73 | 14.50 |
|  | 987,172 | 7 | 7.07 | 11.13 | 16.39 |
|  |  | **Overall** | **7.10** | **11.00** | **15.41** |
| Without ROWID, extra index | 17,000 | 2 | 7.06 | 10.78 | 14.31 |
|  | 510,001 | 5 | 7.60 | 11.69 | 17.25 |
|  | 987,172 | 7 | 7.20 | 11.17 | 15.27 |
|  |  | **Overall** | **7.28** | **11.32** | **15.91** |

### Random access
* Fetch 500 random doujinshi between `id_start` and `id_end`.
* Results:

| Configuration | id_start | id_end | avg | p95 | p99 |
|---|---|:---:|---|---|---|
| With ROWID, no extra index | 100 | 50,000 | 6.69 | 10.74 | 12.28 |
|  | 470,011 | 610,010 | 6.68 | 10.75 | 12.15 |
|  | 700,001 | 1,000,000 | 6.70 | 10.57 | 12.63 |
|  |  | **Overall** | **6.69** | **10.74** | **12.30** |
| With ROWID, extra index | 100 | 50,000 | 6.72 | 10.82 | 12.24 |
|  | 470,011 | 610,010 | 6.95 | 11.30 | 15.44 |
|  | 700,001 | 1,000,000 | 6.58 | 10.42 | 11.93 |
|  |  | **Overall** | **6.75** | **10.90** | **12.63** |
| Without ROWID, no extra index | 100 | 50,000 | 7.36 | 11.77 | 14.32 |
|  | 470,011 | 610,010 | 7.51 | 12.01 | 15.47 |
|  | 700,001 | 1,000,000 | 7.52 | 11.68 | 15.66 |
|  |  | **Overall** | **7.47** | **11.84** | **15.28** |
| Without ROWID, extra index | 100 | 50,000 | 7.70 | 12.16 | 15.00 |
|  | 470,011 | 610,010 | 7.48 | 11.86 | 15.28 |
|  | 700,001 | 1,000,000 | 7.57 | 11.60 | 16.51 |
|  |  | **Overall** | **7.59** | **11.90** | **15.55** |