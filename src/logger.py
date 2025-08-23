# TODO: switch from per-function logging to error-type-based
import logging

from .database_status import DatabaseStatus
from .models import Doujinshi
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


class DatabaseLogger:
	def __init__(self, name, log_path, file_format=None, stream_format=None):
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)

		if not file_format:
			self.file_format = "%(levelname)s, %(asctime)s %(name)s, %(funcName)s, %(message)s"
		else:
			self.file_format = file_format
		self.file_handler = logging.FileHandler(log_path, encoding="utf-8")
		self.file_handler.setLevel(logging.DEBUG)
		file_formatter = logging.Formatter(self.file_format)
		self.file_handler.setFormatter(file_formatter)

		if not stream_format:
			self.stream_format = "%(levelname)s, %(name)s, %(funcName)s, %(message)s"
		else:
			self.stream_format = stream_format
		self.stream_handler = logging.StreamHandler()
		self.stream_handler.setLevel(logging.DEBUG)
		stream_formatter = logging.Formatter(self.stream_format)
		self.stream_handler.setFormatter(stream_formatter)

		self.enable()


	def enable(self):
		self.logger.addHandler(self.file_handler)
		self.logger.addHandler(self.stream_handler)


	def disable(self):
		self.logger.removeHandler(self.file_handler)
		self.logger.removeHandler(self.stream_handler)


	def success(self, status, msg, stacklevel=3):
		self.logger.info(f"{status.name}. {msg}", stacklevel=stacklevel)


	def exception(self, status, exception, stacklevel=3):
		msg = f"{status.name}. Unexpected exception. More details below.\n{type(exception).__name__}: {exception}"
		self.logger.error(msg, stacklevel=stacklevel)


	def validation_failed(self, status, stacklevel=2):
		msg = f"{status.name}. Doujinshi validation failed. Insertion skipped."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_not_found(self, status, model, item_name, stacklevel=3):
		if model is Doujinshi:
			msg = f"{status.name}. [doujinshi] #{item_name} doesn't exist."
		else:
			msg = f"{status.name}. [{model.__tablename__}] value not found: {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_duplicate(self, status, model, item_name, stacklevel=3):
		if model is Doujinshi:
			msg = f"{status.name}. [doujinshi] duplicate ID: #{item_name}."
		else:
			msg = f"{status.name}. [{model.__tablename__}] duplicate value: {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_inserted(self, status, model, item_name, stacklevel=3):
		if model is Doujinshi:
			msg = f"{status.name}. [doujinshi] inserted new value: #{item_name}."
		else:
			msg = f"{status.name}. [{model.__tablename__}] inserted new value: {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def doujinshi_item_linked(self, status, model, item_name, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. Linked [doujinshi] #{doujinshi_id} <--> [{model.__tablename__}] {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def doujinshi_item_duplicate(self, status, model, item_name, doujinshi_id, stacklevel=3):
		msg = f"{status.name}, [doujinshi] #{doujinshi_id} already has: [{model.__tablename__}] {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_added_to_doujinshi(self, status, model, item_name, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. [doujinshi] #{doujinshi_id} now includes: [{model.__tablename__}] {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def page_duplicate(self, status, stacklevel=3):
		msg = f"{status.name}. [page] has duplicate filename or order_number."
		self.logger.info(msg, stacklevel=stacklevel)


	def page_inserted(self, status, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. [doujinshi] #{doujinshi_id} has had new pages added."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_not_in_doujinshi(self, status, model, item_name, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. [doujinshi] #{doujinshi_id} has no [{model.__tablename__}] {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_removed_from_doujinshi(self, status, model, item_name, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. [doujinshi] #{doujinshi_id} had [{model.__tablename__}] {item_name!r} removed."
		self.logger.info(msg, stacklevel=stacklevel)


	def doujinshi_removed(self, status, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. [doujinshi] #{doujinshi_id} was removed."
		self.logger.info(msg, stacklevel=stacklevel)


	def path_duplicate(self, status, stacklevel=3):
		path = "{path}"
		msg = f"{status.name}. {path} already exists in another doujinshi."
		self.logger.info(msg, stacklevel=stacklevel)


	def column_updated(self, status, column, value, doujinshi_id, stacklevel=3):
		column = "{" + column + "}"
		msg = f"{status.name}. [doujinshi] #{doujinshi_id} has updated column {column} to {value!r}."
		self.logger.info(msg, stacklevel=stacklevel)