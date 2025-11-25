from enum import Enum


class OperationType(Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    READ = 'READ'
    FAILED = 'FAILED'
