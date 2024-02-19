import os
import json
from models.config.file_types_config import AcceptedFileTypes

def getAcceptedFileTypeConfig() -> AcceptedFileTypes:
    configFile = open(f'{os.getcwd()}/config/FileTypesConfig.json')
    config = AcceptedFileTypes.model_validate(json.load(configFile))
    return config
