import logging
from logging.handlers import RotatingFileHandler
from .database_status import DatabaseStatus
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
		log_record = {}
		
		if self.include_level:
			log_record["level"] = record.levelname
		if self.include_logger:
			log_record["logger"] = record.name
		if self.include_time:
			log_record["time"] = self.formatTime(record, datefmt="UTC %Y-%m-%d %H:%M:%S")

		log_record["func"] = record.funcName
		log_record["msg"] = record.getMessage()
		
		if hasattr(record, "extra_data"):
			log_record.update(record.extra_data)

		return json.dumps(log_record, ensure_ascii=False, indent=self.indent)


class DatabaseLogger:
	def __init__(self, name, log_path):
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)

		self.file_handler = RotatingFileHandler(
			log_path,
			maxBytes=10*1024*1024, # 50 MB
			backupCount=50,
			encoding="utf-8"
		)
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


	def remove_handlers(self):
		loggers_to_remove = [logger for logger in self.logger.handlers]

		for logger in loggers_to_remove:
			self.logger.removeHandler(logger)


	def enable(self):
		self.remove_handlers() # to prevent duplicate handlers

		self.logger.addHandler(self.file_handler)
		self.logger.addHandler(self.stream_handler)


	def disable(self):
		self.remove_handlers()


	def log_event(self, level, status, stacklevel, **kwargs):
		msg = kwargs.pop("msg", "")
		data = {
			"db_status": status.name,
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
		# stacklevel = 1, funcName is the direct caller of this function.
		# stacklevel = 2, funcName is the caller of the direct caller of this function.
		# stacklevel = 3, ...
		self.log_event(logging.INFO, DatabaseStatus.OK, stacklevel+2, msg=msg, **kwargs)


	def exception(self, exception, stacklevel, **kwargs):
		self.log_event(
			logging.ERROR,
			DatabaseStatus.EXCEPTION,
			error_type=type(exception).__name__,
			error_msg=str(exception),
			stacklevel=stacklevel+2,
			**kwargs
		)


	def integrity_error(self, error, stacklevel, **kwargs):
		error_str = str(error)
		# Example:
		# (sqlite3.IntegrityError) UNIQUE constraint failed: parody.name
		# [SQL: INSERT INTO parody (name, count) VALUES (?, ?) RETURNING id]
		# [parameters: ('a', 0)]
		# (Background on this error at: https://sqlalche.me/e/20/gkpj)
		error_message = error_str.split("\n", 1)[0]
		details = "\n".join(error_str.split("\n")[1:-1]) if "\n" in error_str else None

		self.log_event(
			logging.INFO,
			DatabaseStatus.INTEGRITY_ERROR,
			error_msg=error_message,
			error_details=details,
			stacklevel=stacklevel+2,
			**kwargs,
		)


	def validation_failed(self, stacklevel, **kwargs):
		self.log_event(
			logging.INFO,
			DatabaseStatus.VALIDATION_FAILED,
			msg="doujinshi validation failed",
			stacklevel=stacklevel+2,
			**kwargs,
		)


	def not_found(self, what, stacklevel, **kwargs):
		self.log_event(
			logging.INFO,
			DatabaseStatus.NOT_FOUND,
			msg=f"{what} not found",
			stacklevel=stacklevel+2,
			**kwargs,
		)


	def already_exists(self, what, stacklevel, **kwargs):
		self.log_event(
			logging.INFO,
			DatabaseStatus.ALREADY_EXISTS,
			msg=f"{what} already exists",
			stacklevel=stacklevel+2,
			**kwargs,
		)