# SQLite Benchmark Results
Summarize database performance benchmarks. As the title suggests, this is specific to SQLite. Benchmark again when you change the underlying database.

---

## Some definitions
* `Doujinshi`
* `Item type`: One of these: `Parody`, `Character`, `Tag`, `Artist`, `Group`, `Language`, `Page`.
* `Item`: An instance of an item type.
* `Extra index`: A manually created index (`{item_type_id}, doujinshi_id`) on many-to-many table (`doujinshi_{item_type}`) as opposed to the automatically created index (`doujinshi_id, {item_type_id}`).
* **Note**: the underlying name of `Item type` `Group` is `circle` to avoid reserved keyword in SQLite.

---

## 1. Insert doujinshi
* Insert 1,000,000 randomly generated (with fixed seed) `doujinshi` in batches of 10,000.
* Number of items by type:  
  * `Parody`, `Tag`, `Character`, `Artist`, and `Group`: 500 each.
  * `Language`: 4.
  * `Page`: up to 250 per `doujinshi`.
* Run with these flags ([source](https://www.powersync.com/blog/sqlite-optimizations-for-ultra-high-performance#strongstrong1-enable-write-ahead-logging-wal-and-disable-synchronous-modeaccording)):
  * `PRAGMA synchronous = NORMAL;`
  * `PRAGMA journal_mode = WAL;`
  * `PRAGMA temp_store = MEMORY;`
* Item distribution by type:  
  * Each `item type` (except `Page`) has a **97%** chance to sample without replacement a random number of items from **base_min** up to **base_max**, and a **3%** chance to sample without replacement a random number of items from **rare_max** up to the total number of items.
  * `Page` has an **85%** chance to sample the number of pages from a Gaussian distribution with **mean 25** and **stddev 7**, and a **15%** chance with **mean 200** and **stddev 50**. The number of pages is **clamped** between **1** and **250**.
* **Note**: `Doujinshi` and `items` are inserted directly into the database using IDs (so no duplicate or violation checks are performed). Therefore, insert time is faster than when using the actual insert method provided by `DatabaseManager`, which will be slower due to validation overhead.

| Item type | base_min | base_max | rare_max |
|-----------|---------:|---------:|---------:|
| Parody    | 0 | 2  | 10  |
| Character | 0 | 4  | 20  |
| Tag       | 0 | 15 | 100 |
| Artist    | 0 | 2  | 30  |
| Group     | 0 | 1  | 3   |
| Language  | 1 | 1  | 2   |

* Results:
  * File size is calculated after running the command `VACUUM`.
  * I drop indices before inserting, then recreate them after to make insertion faster. Thus, insert time is only shown for no `extra index` schema.

| Configuration                 | File size (GB) | Insert time (s) |
|-------------------------------|----------:|--------:|
| With ROWID, no extra index    | 4.2222 | 949.80  |
| With ROWID, extra index       | 4.9560 |         |
| Without ROWID, no extra index | 2.2859 | 1138.58 |
| Without ROWID, extra index    | 2.8133 |         |

* Number of rows inserted:

| Table               |       Rows |
|---------------------|-----------:|
| doujinshi           | 1,000,000  |
| doujinshi_parody    | 8,554,800  |
| doujinshi_character | 9,813,695  |
| doujinshi_tag       | 16,264,622 |
| doujinshi_artist    | 8,994,647  |
| doujinshi_circle    | 8,029,873  |
| doujinshi_language  | 1,060,181  |
| page                | 50,089,160 |
| **Total**           | **103,806,978** |

> **TLDR**: ROWID tables are ~2x larger than WITHOUT ROWID, but insertion times are comparable.

---

## 2. update_count_of_all
* **DEPRECATED**: This section is now redundant. All count updates are now auto handled by triggers.
* Measure in **seconds** how long it takes to count how many `doujinshi` each `item type` has.
* Run **n_times** times.
* Results:

| Configuration                 | n_times | min | max | avg |
|-------------------------------|--------:|----:|----:|----:|
| With ROWID, no extra index    | 10  | 18.48 | 19.89 | 19.50 |
| With ROWID, extra index       | 100 | 3.02  | 3.73  | 3.18  |
| Without ROWID, no extra index | 10  | 16.55 | 20.44 | 18.25 |
| Without ROWID, extra index    | 100 | 2.67  | 6.60  | 3.05  |

> **TLDR**: Extra index is critical.

---

## 3. get_doujinshi
* Measure in **milliseconds** how long it takes to retrieve 1 `doujinshi` from database.
* Report metrics: average (**avg**), 95th percentile (**p95**), 99th percentile (**p99**).
* Each run has a warm-up: fetch **20** `doujinshi` at evenly spaced IDs from 1 to 1,000,000.

### Predictable access
* Fetch **1,000** `doujinshi` starting from **id_start**, with step size **step**.
* Results:

| Configuration | id_start | step | avg | p50 | p95 | p99 |
|---------------|---------:|-----:|----:|----:|----:|----:|
| With ROWID, no extra index    | 3,000   | 2 | 1.57 | 1.50 | 2.02 | 2.35 |
|                               | 499,799 | 4 | 1.55 | 1.47 | 2.02 | 2.60 |
|                               | 975,172 | 7 | 1.57 | 1.51 | 2.04 | 2.36 |
| |  | **Overall**                            | **1.56** | **1.50** | **2.03** | **2.45** |
| With ROWID, extra index       | 3,000   | 2 | 1.60 | 1.51 | 2.10 | 2.38 |
|                               | 499,799 | 4 | 1.72 | 1.59 | 2.41 | 3.19 |
|                               | 975,172 | 7 | 1.70 | 1.61 | 2.25 | 2.66 |
|  |  | **Overall**                           | **1.68** | **1.58** | **2.23** | **2.93** |
| Without ROWID, no extra index | 3,000   | 2 | 1.63 | 1.53 | 2.23 | 2.57 |
|                               | 499,799 | 4 | 1.71 | 1.58 | 2.37 | 3.39 |
|                               | 975,172 | 7 | 1.67 | 1.58 | 2.24 | 2.72 |
|  |  | **Overall**                           | **1.67** | **1.57** | **2.27** | **2.87** |
| Without ROWID, extra index    | 3,000   | 2 | 1.60 | 1.49 | 2.17 | 2.67 |
|                               | 499,799 | 4 | 1.65 | 1.55 | 2.12 | 2.54 |
|                               | 975,172 | 7 | 1.71 | 1.58 | 2.34 | 3.21 |
|  |  | **Overall**                           | **1.65** | **1.55** | **2.22** | **2.78** |

### Random access
* Fetch **1,000** random `doujinshi` between **id_start** and **id_end**.
* Results:

| Configuration | id_start | id_end | avg | p50 | p95 | p99 |
|---------------|---------:|-------:|----:|----:|----:|----:|
| With ROWID, no extra index    | 100     | 50,000    | 2.55 | 2.39 | 3.43 | 4.41 |
|                               | 470,011 | 610,010   | 2.61 | 2.48 | 3.37 | 3.93 |
|                               | 700,001 | 1,000,000 | 2.68 | 2.53 | 3.55 | 4.10 |
|  |  | **Overall**                                   | **2.61** | **2.48** | **3.44** | **4.23** |
| With ROWID, extra index       | 100     | 50,000    | 2.72 | 2.54 | 3.75 | 4.56 |
|                               | 470,011 | 610,010   | 3.02 | 2.77 | 4.22 | 5.57 |
|                               | 700,001 | 1,000,000 | 2.79 | 2.68 | 3.65 | 4.12 |
|  |  | **Overall**                                   | **2.84** | **2.67** | **3.86** | **4.68** |
| Without ROWID, no extra index | 100     | 50,000    | 2.99 | 2.81 | 4.12 | 4.60 |
|                               | 470,011 | 610,010   | 3.18 | 2.95 | 4.57 | 5.72 |
|                               | 700,001 | 1,000,000 | 3.08 | 2.91 | 4.14 | 4.81 |
|  |  | **Overall**                                   | **3.09** | **2.90** | **4.24** | **5.21** |
| Without ROWID, extra index    | 100     | 50,000    | 1.72 | 1.64 | 2.27 | 2.54 |
|                               | 470,011 | 610,010   | 1.83 | 1.71 | 2.42 | 3.17 |
|                               | 700,001 | 1,000,000 | 1.76 | 1.67 | 2.27 | 2.62 |
|  |  | **Overall**                                   | **1.77** | **1.67** | **2.30** | **2.87** |


> **TLDR**: Without ROWID, extra index is the fastest.

---

## 4. get_doujinshi_in_page
* Measure in **milliseconds** how long it takes to fetch 1 page.
* Each page has 25 doujinshi (`id`, `full_name`, `path`, `cover_filename`). Note that page here is different from the item type `page`.
* Use WITHOUT ROWID, extra index.
* Fetch from **page_start** to **page_end**, shuffled.
* The first iteration has this (ORM translated to) SQL:
```sql
SELECT
    doujinshi.id,
    doujinshi.full_name,
    doujinshi.path,
    page.filename
FROM doujinshi
JOIN page ON doujinshi.id = page.doujinshi_id
WHERE page.order_number = 1
ORDER BY doujinshi.id DESC
LIMIT 25
OFFSET :page_number
```
(commit fc7abf8e7541e303c72cc621be7b7770975da36f has a redundant WHERE clause)

I only fetch **10** pages, the reason why is explained below (results below are BEFORE fetching primary language):

| page_start | page_end | avg | p50 | p95 | p99 |
|-----------:|---------:|----:|----:|----:|----:|
| 1      | 11     | 371.56 | 344.04 | 507.29  | 561.17  |
| 19,995 | 20,005 | 806.72 | 813.55 | 856.24  | 865.09  |
| 39,990 | 40,000 | 858.97 | 823.44 | 1001.40 | 1004.65 |

Nearly **0.5** seconds to fetch a random first 10 pages and **1** second to fetch a random last 10 pages. My short-attention-span brain can't wait this long. Unacceptable!!!

* Rewrite the SQL to only fetch `page.filename` after getting `doujinishi.id`:
```sql
SELECT
    doujinshi.id,
    doujinshi.full_name,
    doujinshi.path,
    (
        SELECT page.filename
        FROM page
        WHERE page.doujinshi_id = doujinshi.id AND page.order_number = 1
    ) AS filename
FROM doujinshi
ORDER BY doujinshi.id DESC
LIMIT 25
OFFSET :page_number
```

Now I can confidently fetch **500** pages (results below are BEFORE fetching primary language).

| page_start | page_end | avg | p50 | p95 | p99 |
|-----------:|---------:|----:|----:|----:|----:|
| 1      | 501    | 0.54  | 0.52  | 0.64  | 0.91  |
| 19,750 | 20,250 | 10.22 | 10.08 | 11.22 | 11.98 |
| 39,500 | 40,000 | 20.71 | 20.47 | 22.32 | 24.98 |

* Fetching the last pages is slow because the db has to scan top-down. But why do that when I can scan bottom-up? I can cache `total_page`, and if `page_number > total_page / 2`, just reverse the scan order. After pulling my hair finding the correct `LIMIT` and `OFFSET` and wrestling with test cases, here’s the result (AFTER fetching primary language):

| page_start | page_end | avg | p50 | p95 | p99 |
|-----------:|---------:|----:|----:|----:|----:|
| 1      | 501    | 0.86  | 0.81  | 0.92  | 1.11  |
| 19,750 | 20,250 | 22.37 | 21.76 | 26.92 | 29.53 |
| 39,500 | 40,000 | 0.92  | 0.90  | 1.10  | 1.43  |

Much better (I even had music playing in the background during benchmarking — except for the painfully slow first run).

> **TLDR**: Fast enough.

---

## 5. insert_doujinshi
* Measure in **milliseconds** how long it takes to insert 1 doujinshi into the database.
* This is done after inserting **1,000,000** doujinshi.
* Use WITHOUT ROWID, extra index.
* Result across **1,000** runs:

| avg | p50 | p95 | p99 |
|----:|----:|----:|----:|
| 19.18 | 8.31 | 48.42 | 84.06 |

> **TLDR**: Fast enough for single use.

---

## 6. Conclusion (if this is the final version of this benchmark)
* Use WITHOUT ROWID. WITH and WITHOUT ROWID tables perform almost the same in terms of time, but WITHOUT ROWID uses significant less storage.