import os
config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structFormatter': {
            'class': 'logging.Formatter',
            'format': '%(message)s'
        }
    },
    'handlers': {
        'consoleHandler': {
            'class': 'logging.StreamHandler',
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
