import os
import json
from models.config.file_types_config import AcceptedFileTypes


def get_accepted_file_type_config() -> AcceptedFileTypes:
    config_file = open(f'{os.getcwd()}/src/config/FileTypesConfig.json')
    config = AcceptedFileTypes.model_validate(json.load(config_file))
    return config
