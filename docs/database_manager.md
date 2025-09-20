# class src.DatabaseManager
Manager for database connections.

This class provides a high-level interface for interacting with the underlying database. It is responsible for creating and managing the SQLAlchemy session, executing queries, and handling transactions.

For usage examples, refer to [TODO: UPDATE HERE](a).

> [!NOTE]
> - This class (currently) is specific to **SQLite**.  
> - Call `update_count` methods after any update operations, since update methods themselves don't update the counts.
> - All CRUD methods are atomic.
> - When inserting a doujinshi, its `item` names (except `pages`) should be in lowercase.


# Methods
## GENERAL / DATABASE-LEVEL methods
__DatabaseManager(*url, log_path, echo*__*=False*__*, test*__*=False*__)__
- __Parameters:__
  - __url : *str*__\
    The database connection path to establish the connection.
  - __log_path : *str*__\
    Path to the log file where database operations will be logged.
  - __echo : *bool, default=False*__\
    If True, the database engine will emit all SQL statements.
  - __test : *bool, default=False*__\
    If True, initializes the database in testing mode (remember to set `url` to use an in-memory database).

__session()__\
Return this database's internal session.
- __Returns:__
  - __session : *sqlalchemy.orm.Session*__\
    The internal session associated with this object.


__create_database()__\
Creates database schema.

Does these things:
- Create database tables defined in the SQLAlchemy `Base` metadata.
- Create `extra indices`.
- Create `triggers`.
- Inserts a set of default languages (__"english"__, __"japanese"__, __"textless"__, __"chinese"__).

Does nothing if a schema already exists.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - database created.

__enable_logger()__\
Enable (stream and file) logger.

__disable_logger()__\
Disable (stream and file) logger.

__create_index()__\
(Re)Create `extra indices`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `extra indices` created.

__drop_index()__\
Drop `extra indices`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `extra indices` dropped.

__show_index()__\
Print all indices in the database.

__vacuum()__\
Execute the SQLite command `VACUUM` to reduce storage size.\
Use this after bulk inserts or creating indices.\
Other databases may have a different command for this operation.

---

## READ methods
__how_many_doujinshi()__\
Get the total number of `doujinshi` in the database.
- __Returns:__
  - __count : *int*__\
    The total number of `doujinshi` in the database.

__get_doujinshi(*doujinshi_id*)__\
Retrieve a __full-data__ `doujinshi` by ID.\
Use this method when routing to */g/{id}*.\
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to retrieve.
- __Returns:__
  - __doujinshi : *dict or None*__\
    A dict if found, otherwise None, containing these fields:
      - Single-valued: 'id', 'path', 'note', 'full_name', 'full_name_original', 'pretty_name', 'pretty_name_original',
      - `Item`-count dict: 'parodies', 'characters', 'tags', 'artists', 'groups', 'languages' (guaranteed to be sorted),
      - List-like: 'pages' (in order).

__get_doujinshi_in_page(*page_size, page_number, n_doujinshis*__*=None*__)__\
Retrieve a paginated list of latest (by ID) __partial-data__ `doujinshi`.\
Use this method when routing to */?page={page_number}*.
- __Parameters:__
  - __page_size : *int*__\
    Number of `doujinshi` per page.
  - __page_number : *int*__\
    Page number to retrieve (1-based).
  - __n_doujinshi : *int, default=None*__\
    Total number of `doujinshi`. If not None, this value is used to optimize retrieval of later pages.
- __Returns:__
  - __doujinshi_list : *list of dict*__\
    Each dict contains the these fields: 'id' 'full_name' 'path' 'cover_filename' and 'language_id'. 'language_id' mapping is as follows:
      - `None`: no language,
      - `1`: english,
      - `2`: japanese,
      - `3`: chinese,
      - `4`: textless.

__get_doujinshi_in_range(*id_start*__*=1*__, id_end__*=None*__)__\
Retrieve all __full-data__ `doujinshi` in an ID range.\
Use this method when exporting or serializing data.
- __Parameters:__
  - __id_start : *int, default=1*__\
    Start ID of the range (inclusive).
  - __id_end : *int, default=None*__\
    End ID of the range (inclusive). If None, retrieves all doujinshi from *id_start*.
- __Returns:__
  - __doujinshi_list : *list of dict*__\
    A list of dict representing doujinshi, expected fields:
      - Single-valued: 'id', 'path', 'note', 'full_name', 'full_name_original', 'pretty_name', 'pretty_name_original',
      - List-like: 'parodies', 'characters', 'tags', 'artists', 'groups', 'languages' (guaranteed to be sorted), 'pages' (in order).

__get_count_of_parodies(*names*)__\
Get the number of `doujinshi` associated with each `parody`.
- __Parameters:__
  - __names : *list of str*__\
    Names of the `parodies` to retrieve counts for.
- __Returns:__
  - __count_dict : *dict*__\
    Dictionary mapping `parody` names to their counts.

__get_count_of_characters(*names*)__\
Get the number of `doujinshi` associated with each `character`.
- __Parameters:__
  - __names : *list of str*__\
    Names of the `characters` to retrieve counts for.
- __Returns:__
  - __count_dict : *dict*__\
    Dictionary mapping `character` names to their counts.

__get_count_of_tags(*names*)__\
Get the number of `doujinshi` associated with each `tag`.
- __Parameters:__
  - __names : *list of str*__\
    Names of the `tags` to retrieve counts for.
- __Returns:__
  - __count_dict : *dict*__\
    Dictionary mapping `tag` names to their counts.

__get_count_of_artists(*names*)__\
Get the number of `doujinshi` associated with each `artist`.
- __Parameters:__
  - __names : *list of str*__\
    Names of the `artists` to retrieve counts for.
- __Returns:__
  - __count_dict : *dict*__\
    Dictionary mapping `artist` names to their counts.

__get_count_of_groups(*names*)__\
Get the number of `doujinshi` associated with each `group`.
- __Parameters:__
  - __names : *list of str*__\
    Names of the `groups` to retrieve counts for.
- __Returns:__
  - __count_dict : *dict*__\
    Dictionary mapping `group` names to their counts.

__get_count_of_languages(*names*)__\
Get the number of `doujinshi` associated with each `language`.
- __Parameters:__
  - __names : *list of str*__\
    Names of the `languages` to retrieve counts for.
- __Returns:__
  - __count_dict : *dict*__\
    Dictionary mapping `language` names to their counts.

---

## CREATE methods
__insert_parody(*name*)__\
Insert a `parody` into the database.
- __Parameters:__
  - __name : *str*__\
    Name of the `parody` to insert, automatically stripped of leading/trailing/between-word whitespace and converted to lowercase.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `parody` inserted.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `parody` already exists.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__insert_character(*name*)__\
Insert a `character` into the database.
- __Parameters:__
  - __name : *str*__\
    Name of the `character` to insert, automatically stripped of leading/trailing/between-word whitespace and converted to lowercase.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `character` inserted.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `character` already exists.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__insert_tag(*name*)__\
Insert a `tag` into the database.
- __Parameters:__
  - __name : *str*__\
    Name of the `tag` to insert, automatically stripped of leading/trailing/between-word whitespace and converted to lowercase..
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `tag` inserted.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `tag` already exists.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__insert_artist(*name*)__\
Insert an `artist` into the database.
- __Parameters:__
  - __name : *str*__\
    Name of the `artist` to insert, automatically stripped of leading/trailing/between-word whitespace and converted to lowercase.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `artist` inserted.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `artist` already exists.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__insert_group(*name*)__\
Insert a `group` into the database.
- __Parameters:__
  - __name : *str*__\
    Name of the `group` to insert, automatically stripped of leading/trailing/between-word whitespace and converted to lowercase.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `group` inserted.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `group` already exists.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__insert_language(*name*)__\
Insert a `language` into the database.
- __Parameters:__
  - __name : *str*__\
    Name of the `language` to insert, automatically stripped of leading/trailing/between-word whitespace and converted to lowercase.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `language` inserted.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `language` already exists.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__insert_doujinshi(*doujinshi, user_prompt*__*=True*__)__\
Insert a single `doujinshi` into the database.
- __Parameters:__
  - __doujinshi : *dict*__\
    A dict containing doujinshi data. Expected fields:
      - Single-valued: 'id', 'path', 'note', 'full_name', 'full_name_original', 'pretty_name', 'pretty_name_original',
      - List of str: 'parodies', 'characters', 'tags', 'artists', 'groups', 'languages', 'pages'.
  - __user_prompt : *bool, default=True*__\
    Whether to prompt the user during doujinshi validation.\
    If all doujinshi fields are already filled, no prompt is shown.\
    If False, validation will not alert user about empty list-like fields or warnings.
- __Returns:__
- __status : *DatabaseStatus*__\
  Status of the operation.
  - __*DatabaseStatus.OK*__ - `doujinshi` inserted.
  - __*DatabaseStatus.VALIDATION_FAILED*__ - validation failed.
  - __*DatabaseStatus.ALREADY_EXISTS*__ - `doujinshi`'s ID already exists.
  - __*DatabaseStatus.INTEGRITY_ERROR*__ - integrity errors (likely "path" uniqueness violation).
  - __*DatabaseStatus.EXCEPTION*__ - other errors.

---

## UPDATE methods
__add_parody_to_doujinshi(*doujinshi_id, name*)__\
Add an existing `parody` to an existing `doujinshi` by name.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `parody` should be added.
  - __name : *str*__\
    Name of the `parody` to add.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `parody` added.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `parody` already linked to `doujinshi`.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `parody` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__add_character_to_doujinshi(*doujinshi_id, name*)__\
Add an existing `character` to an existing `doujinshi` by name.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `character` should be added.
  - __name : *str*__\
    Name of the `character` to add.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `character` added.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `character` already linked to `doujinshi`.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `character` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__add_tag_to_doujinshi(*doujinshi_id, name*)__\
Add an existing `tag` to an existing `doujinshi` by name.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `tag` should be added.
  - __name : *str*__\
    Name of the `tag` to add.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `tag` added.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `tag` already linked to `doujinshi`.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `tag` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__add_artist_to_doujinshi(*doujinshi_id, name*)__\
Add an existing `artist` to an existing `doujinshi` by name.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `artist` should be added.
  - __name : *str*__\
    Name of the `artist` to add.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `artist` added.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `artist` already linked to `doujinshi`.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `artist` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__add_group_to_doujinshi(*doujinshi_id, name*)__\
Add an existing `group` to an existing `doujinshi` by name.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `group` should be added.
  - __name : *str*__\
    Name of the `group` to add.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `group` added.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `group` already linked to `doujinshi`.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `group` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__add_language_to_doujinshi(*doujinshi_id, name*)__\
Add an existing `language` to an existing `doujinshi` by name.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `language` should be added.
  - __name : *str*__\
    Name of the `language` to add.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `language` added.
    - __*DatabaseStatus.ALREADY_EXISTS*__ - `language` already linked to `doujinshi`.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `language` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__add_pages_to_doujinshi(*doujinshi_id, pages*)__\
Remove old `pages` and then add new `pages` to an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to which the `pages` should be added.
  - __pages : *list of str, default=None*__\
    Filenames of the new `pages` in order.
    If None or empty, doujinshi's `pages` are removed.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `pages` added.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - integrity error (likely duplicate "filename").
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_parody_from_doujinshi(*doujinshi_id, name*)__\
Remove a `parody` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which the `parody` should be removed.
  - __name : *str*__\
    Name of the `parody` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `parody` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `parody` not found, or `parody` not associated with `doujinshi`.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_character_from_doujinshi(*doujinshi_id, name*)__\
Remove a `character` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which the `character` should be removed.
  - __name : *str*__\
    Name of the `character` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `character` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `character` not found, or `character` not associated with `doujinshi`.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_tag_from_doujinshi(*doujinshi_id, name*)__\
Remove a `tag` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which the `tag` should be removed.
  - __name : *str*__\
    Name of the `tag` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `tag` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `tag` not found, or `tag` not associated with `doujinshi`.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_artist_from_doujinshi(*doujinshi_id, name*)__\
Remove an `artist` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which the `artist` should be removed.
  - __name : *str*__\
    Name of the `artist` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `artist` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `artist` not found, or `artist` not associated with `doujinshi`.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_group_from_doujinshi(*doujinshi_id, name*)__\
Remove a `group` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which the `group` should be removed.
  - __name : *str*__\
    Name of the `group` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `group` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `group` not found, or `group` not associated with `doujinshi`.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_language_from_doujinshi(*doujinshi_id, name*)__\
Remove a `language` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which the `language` should be removed.
  - __name : *str*__\
    Name of the `language` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `language` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` or `language` not found, or `language` not associated with `doujinshi`.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__remove_all_pages_from_doujinshi(*doujinshi_id*)__\
Remove all `pages` from an existing `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` from which all the `pages` should be removed.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `pages` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_full_name_of_doujinshi(*doujinshi_id, value*)__\
Update the full name of a `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` whose full name will be updated.
  - __value : *str*__
    New full name.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - full name updated.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - full name is not a non-empty string.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_full_name_original_of_doujinshi(*doujinshi_id, value*)__\
Update the original full name of a `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` whose original full name will be updated.
  - __value : *str*__
    New original full name.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - original full name updated.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - original full name is not a non-empty string.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_pretty_name_of_doujinshi(*doujinshi_id, value*)__\
Update the pretty name of a `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` whose pretty name will be updated.
  - __value : *str*__
    New pretty name.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - pretty name updated.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - pretty name is not a non-empty string.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_pretty_name_original_of_doujinshi(*doujinshi_id, value*)__\
Update the original pretty name of a `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` whose original pretty name will be updated.
  - __value : *str*__
    New original pretty name.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - original pretty name updated.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - original pretty name is not a non-empty string.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_note_of_doujinshi(*doujinshi_id, value*)__\
Update the note of a `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` whose note will be updated.
  - __value : *str*__
    New note.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - note updated.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - note is not a non-empty string.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_path_of_doujinshi(*doujinshi_id, value*)__\
Update the path of a `doujinshi`.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` whose path will be updated.
  - __value : *str*__
    New path.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - path updated.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.INTEGRITY_ERROR*__ - path is not a non-empty string or not unique.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.

__update_count_of_parody()__\
Update count of all `parodies`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - count updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

__update_count_of_character()__\
Update count of all `characters`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - count updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

__update_count_of_tag()__\
Update count of all `tags`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - count updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

__update_count_of_artist()__\
Update count of all `artists`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - count updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

__update_count_of_group()__\
Update count of all `groups`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - count updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

__update_count_of_language()__\
Update count of all `languages`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - count updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

__update_count_of_all()__\
Update counts of all `items`.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - all counts updated.
    - __*DatabaseStatus.EXCEPTION*__ - error occurred.

## DELETE methods
__remove_doujinshi(*doujinshi_id*)__\
Remove a `doujinshi` from the database by ID.\
All of its related `items` (`parodies`, `characters`, `tags`, `artists`, `groups`, `languages`, `pages`) will be removed as well.
- __Parameters:__
  - __doujinshi_id : *int*__\
    ID of the `doujinshi` to remove.
- __Returns:__
  - __status : *DatabaseStatus*__\
    Status of the operation.
    - __*DatabaseStatus.OK*__ - `doujinshi` removed.
    - __*DatabaseStatus.NOT_FOUND*__ - `doujinshi` not found.
    - __*DatabaseStatus.EXCEPTION*__ - other errors.