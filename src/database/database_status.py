from enum import Enum, auto


class DatabaseStatus(Enum):
	def __new__(cls, *args, **kwds):
		value = len(cls.__members__) + 1
		obj = object.__new__(cls)
		obj._value_ = value
		return obj


	def __init__(self, is_fatal):
		self.is_fatal = is_fatal


	OK = False
	INTEGRITY_ERROR = False
	VALIDATION_FAILED = False
	NOT_FOUND = False
	ALREADY_EXISTS = False

	EXCEPTION = True