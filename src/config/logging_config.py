import os
config = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation_id': {
            '()': 'asgi_correlation_id.CorrelationIdFilter',
            'uuid_length': 32,
            'default_value': '-',
            },
        },
    'formatters': {
        'structFormatter': {
            'class': 'logging.Formatter',
            'format': '[%(correlation_id)s] %(message)s'
        }
    },
    'handlers': {
        'consoleHandler': {
            'class': 'logging.StreamHandler',
            'filters': ['correlation_id'],
            'level': 'DEBUG',
            'formatter': 'structFormatter'
        }
    },
    'loggers': {
        'root': {
            'handlers': ['consoleHandler'],
            'level': os.getenv('LOGGING_LEVEL_ROOT', 'INFO'),
            'propagate': False,
            'qualname': 'root'
        },
        '__main__': {
            'handlers': ['consoleHandler'],
            'level': os.getenv('LOGGING_LEVEL_MAIN', 'INFO'),
            'propagate': False,
            'qualname': '__main__'
        },
        'laa_secure_document_storage_api_app': {
            'handlers': ['consoleHandler'],
            'level': os.getenv('LOGGING_LEVEL_SDSAPI', 'INFO'),
            'propagate': False,
            'qualname': 'src'
        },
        'casbin': {
            'handlers': ['consoleHandler'],
            'level': os.getenv('LOGGING_LEVEL_CASBIN', 'INFO'),
            'propagate': False,
            'qualname': 'casbin'
        }
    }
}
