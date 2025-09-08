import logging

from .database_status import DatabaseStatus
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import json
import time


class JsonFormatter(logging.Formatter):
	converter = time.gmtime

	def __init__(self, include_time, include_level, include_logger, indent):
		super().__init__()
		self.include_time = include_time
		self.include_level = include_level
		self.include_logger = include_logger
		self.indent = indent


	def format(self, record):
		log_record = {
			"function": record.funcName,
			"message": record.getMessage()
		}

		if self.include_logger:
			log_record["logger"] = record.name
		if self.include_time:
			log_record["time"] = self.formatTime(record, datefmt="UTC %Y-%m-%d %H:%M:%S")
		if self.include_level:
			log_record["level"] = record.levelname
		if hasattr(record, "extra_data"):
			log_record.update(record.extra_data)

		return json.dumps(log_record, ensure_ascii=False, indent=self.indent)


class DatabaseLogger:
	def __init__(self, name, log_path):
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)

		self.file_handler = logging.FileHandler(log_path, encoding="utf-8")
		self.file_handler.setLevel(logging.DEBUG)
		self.file_handler.setFormatter(
			JsonFormatter(include_time=True, include_level=True, include_logger=True, indent=None)
		)

		self.stream_handler = logging.StreamHandler()
		self.stream_handler.setLevel(logging.DEBUG)
		self.stream_handler.setFormatter(
			JsonFormatter(include_time=False, include_level=False, include_logger=False, indent=None)
		)

		self.logger.addHandler(self.file_handler)
		self.logger.addHandler(self.stream_handler)


	def log_event(self, level, status, stacklevel, **kwargs):
		msg = kwargs.pop("message", "")
		data = {
			"database_status": status.name,
		}
		if kwargs:
			data.update(kwargs)

		self.logger.log(
			level,
			msg,
			extra={"extra_data": data},
			stacklevel=stacklevel,
		)


	def success(self, msg, stacklevel, **kwargs):
		# stacklevel = 0, funcName is the direct caller of this function.
		# stacklevel = 1, funcName is the caller of the direct caller of this function.
		# stacklevel = 2, ...
		self.log_event(logging.INFO, DatabaseStatus.OK, stacklevel+3, message=msg, **kwargs)


	def exception(self, status, error: Exception, **kwargs):
		self.log_event(
			logging.ERROR,
			status,
			"exception",
			error_type=type(error).__name__,
			error_message=str(error),
			**kwargs,
		)


	def integrity_error(self, status, error: IntegrityError, **kwargs):
		msg = str(error)
		self.log_event(
			logging.ERROR,
			status,
			"integrity_error",
			error_type="IntegrityError",
			error_message=msg.split("\n", 1)[0],
			details="\n".join(msg.split("\n")[1:]) if "\n" in msg else None,
			**kwargs,
		)


# success(self, status, msg, stacklevel=3):
# exception(self, status, exception, stacklevel=3):
# validation_failed(self, status, stacklevel=2):
# item_not_found(self, status, model, item_name, stacklevel=3):
# item_duplicate(self, status, model, item_name, stacklevel=3):
# item_inserted(self, status, model, item_name, stacklevel=3):
# doujinshi_item_linked(self, status, model, item_name, doujinshi_id, stacklevel=3):
# doujinshi_item_duplicate(self, status, model, item_name, doujinshi_id, stacklevel=3):
# item_added_to_doujinshi(self, status, model, item_name, doujinshi_id, stacklevel=3):
# page_duplicate(self, status, stacklevel=3):
# page_inserted(self, status, doujinshi_id, stacklevel=3):
# item_not_in_doujinshi(self, status, model, item_name, doujinshi_id, stacklevel=3):
# item_removed_from_doujinshi(self, status, model, item_name, doujinshi_id, stacklevel=3):
# doujinshi_removed(self, status, doujinshi_id, stacklevel=3):
# path_duplicate(self, status, stacklevel=3):
# column_updated(self, status, column, value, doujinshi_id, stacklevel=3):