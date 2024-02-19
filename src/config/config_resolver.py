import os
import json
from models.config.file_types_config import AcceptedFileTypes

def getAcceptedFileTypeConfig() -> AcceptedFileTypes:
    configFile = open(f'{os.getcwd()}/config/FileTypesConfig.json')
    configJson = json.load(configFile)
    print(configJson)
    config = AcceptedFileTypes.model_validate(configJson)
    return config
