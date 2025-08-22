from enum import Enum, auto


class DatabaseStatus(Enum):
	OK = auto()
	FATAL = auto()
	NON_FATAL_ITEM_DUPLICATE = auto()
	NON_FATAL_ITEM_NOT_FOUND = auto()
	NON_FATAL_VALIDATION_FAILED = auto()