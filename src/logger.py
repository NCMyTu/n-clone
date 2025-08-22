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
		if not stream_format:
			self.stream_format = "%(levelname)s, %(name)s, %(funcName)s, %(message)s"
		else:
			self.stream_format = stream_format

		file_handler = logging.FileHandler(log_path, encoding="utf-8")
		file_handler.setLevel(logging.DEBUG)
		file_formatter = logging.Formatter(self.file_format)
		file_handler.setFormatter(file_formatter)
		self.logger.addHandler(file_handler)

		stream_handler = logging.StreamHandler()
		stream_handler.setLevel(logging.DEBUG)
		stream_formatter = logging.Formatter(self.stream_format)
		stream_handler.setFormatter(stream_formatter)
		self.logger.addHandler(stream_handler)


	def success(self, status, msg, stacklevel=3):
		self.logger.info(f"{status.name}. {msg}", stacklevel=stacklevel)


	def exception(self, status, exception, stacklevel=3):
		msg = f"{status.name}. Unexpected exception.\n{type(exception).__name__}: {exception}"
		self.logger.error(msg, stacklevel=stacklevel)


	def validation_fail(self, status, stacklevel=2):
		msg = f"{status.name}. Doujinshi validation failed. Insertion skipped."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_not_found(self, status, model, item_name, stacklevel=3):
		msg = f"{status.name}. [{model.__tablename__}] value not found: {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_duplicate(self, status, model, item_name, stacklevel=3):
		msg = f"{status.name}. [{model.__tablename__}] duplicate value: {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def doujinshi_duplicate(self, status, doujinshi_id, stacklevel=3):
		self.logger.info(f"{status.name}. [doujinshi] duplicate ID: #{doujinshi_id}.", stacklevel=stacklevel)


	def item_inserted(self, status, model, item_name, stacklevel=3):
		msg = f"{status.name}. [{model.__tablename__}] inserted new value: {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)


	def doujinshi_inserted(self, status, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. [doujinshi] inserted new value: #{doujinshi_id}."
		self.logger.info(msg, stacklevel=stacklevel)


	def item_and_doujinshi_linked(self, status, model, item_name, doujinshi_id, stacklevel=3):
		msg = f"{status.name}. Linked [doujinshi] #{doujinshi_id} <--> [{model.__tablename__}] {item_name!r}."
		self.logger.info(msg, stacklevel=stacklevel)




	def log_insert_item(self, return_status, model, value, exception=None):
		ret_name = return_status.name

		if return_status == DatabaseStatus.OK:
			self.logger.info(
				f"{ret_name}, [{model.__tablename__}] has been inserted into new value: {value!r}.",
				stacklevel=3
			)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE:
			self.logger.info(f"{ret_name} | [{model.__tablename__}] already has value: {value!r}.", stacklevel=3)
		elif return_status == DatabaseStatus.FATAL:
			self.logger.error(
				f"{ret_name} | Unexpected exception.\n{type(exception).__name__}: {exception}", 
				stacklevel=3
			)


	def log_add_item_to_doujinshi(self, return_status, model, value, doujinshi_id=None, exception=None):
		ret_name = return_status.name

		if return_status == DatabaseStatus.OK:
			self.logger.info(
				f"{ret_name} | [doujinshi] #{doujinshi_id} has been added new value: [{model.__tablename__}] {value!r}.",
				stacklevel=3
			)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND:
			if model == Doujinshi:
				self.logger.info(f"{ret_name} | [doujinshi] #{doujinshi_id} doesn't exist.", stacklevel=3)
			else:
				self.logger.info(
					f"{ret_name} | [{model.__tablename__}] doesn't have value: {value!r}. Consider inserting it first.",
					stacklevel=3
				)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE:
			self.logger.info(
				f"{ret_name} | [doujinshi] #{doujinshi_id} already has: [{model.__tablename__}] {value!r}.",
				stacklevel=3
			)
		elif return_status == DatabaseStatus.FATAL:
			self.logger.error(
				f"{ret_name} | Unexpected exception.\n{type(exception).__name__}: {exception}",
				stacklevel=3
			)


	def log_remove_item_from_doujinshi(self, return_status, model, value, doujinshi_id=None, exception=None):
		ret_name = return_status.name

		if return_status == DatabaseStatus.OK:
			# Removals are rare or corrective actions ,
			# log them at WARNING to make them stand out
			self.logger.warning(
				f"{ret_name} | [doujinshi] #{doujinshi_id} has removed: [{model.__tablename__}] {value!r}.",
				stacklevel=3
			)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND:
			if model == Doujinshi:
				self.logger.info(f"{ret_name} | [doujinshi] #{doujinshi_id} doesn't exist.", stacklevel=3)
			else:
				if not doujinshi_id:
					self.logger.info(
						f"{ret_name} | [{model.__tablename__}] doesn't have value: {value!r}.",
						stacklevel=3
					)
				else:
					self.logger.info(
						f"{ret_name} | [doujinshi] #{doujinshi_id} doesn't have value: [{model.__tablename__}] {value!r}.",
						stacklevel=3
					)
		elif return_status == DatabaseStatus.FATAL:
			self.logger.error(
				f"{ret_name} | Unexpected exception.\n{type(exception).__name__}: {exception}",
				stacklevel=3
			)


	def log_add_remove_pages(self, return_status, doujinshi_id, mode=None, exception=None):
		# mode: "remove", "add" or None
		ret_name = return_status.name

		if return_status == DatabaseStatus.OK:
			if mode == "add":
				self.logger.info(
					f"{ret_name} | [doujinshi] #{doujinshi_id} has been added new pages.",
					stacklevel=3
				)
			elif mode == "remove":
				self.logger.warning(
					f"{ret_name} | [doujinshi] #{doujinshi_id} has been removed all its pages.",
					stacklevel=3
				)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND:
			self.logger.info(f"{ret_name} | [doujinshi] #{doujinshi_id} doesn't exist.", stacklevel=3)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_DUPLICATE:
			self.logger.info(f"{ret_name} | [page] likely has duplicate filename or order_number.", stacklevel=3)
		elif return_status == DatabaseStatus.FATAL:
			self.logger.error(
				f"{ret_name} | Unexpected exception.\n{type(exception).__name__}: {exception}",
				stacklevel=3
			)


	def log_remove_doujinshi(self, return_status, doujinshi_id, exception=None):
		ret_name = return_status.name

		if return_status == DatabaseStatus.OK:
			self.logger.warning(f"{ret_name} | [doujinshi] #{doujinshi_id} has been removed.", stacklevel=2)
		elif return_status == DatabaseStatus.NON_FATAL_ITEM_NOT_FOUND:
			self.logger.info(f"{ret_name} | [doujinshi] #{doujinshi_id} doesn't exist.", stacklevel=2)
		elif return_status == DatabaseStatus.FATAL:
			self.logger.error(
				f"{ret_name} | Unexpected exception.\n{type(exception).__name__}: {exception}",
				stacklevel=2
			)