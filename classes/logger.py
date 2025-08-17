import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

class DatabaseLogger:
	def __init__(self, name, log_path, format=None):
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)

		self.format = "%(levelname)s | %(asctime)s | %(name)s | filename: %(filename)s | function: %(funcName)s | %(message)s"

		file_handler = logging.FileHandler(log_path, encoding="utf-8")
		file_handler.setLevel(logging.DEBUG)
		file_formatter = logging.Formatter(self.format)
		file_handler.setFormatter(file_formatter)
		self.logger.addHandler(file_handler)

		console_handler = logging.StreamHandler()
		console_handler.setLevel(logging.DEBUG)
		console_formatter = logging.Formatter(self.format)
		console_handler.setFormatter(console_formatter)
		self.logger.addHandler(console_handler)


	def log_insert(self, is_success, model, value, exception=None):
		if is_success is True:
			self.logger.info(f"Inserted into table [{model.__tablename__}] new value: {value}.", stacklevel=3)
			return

		if isinstance(exception, IntegrityError):
			more_info = "\n".join(str(exception).split("\n")[:-1])
			msg = f"Table [{model.__tablename__}] already has value: {value}.\n{more_info}"
			self.logger.error(msg, stacklevel=3)
		elif isinstance(exception, Exception):
			self.logger.error(f"Unexpected exception.\n{type(exception).__name__}: {exception}", stacklevel=3)