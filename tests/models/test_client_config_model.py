import json
import pytest
from src.models.client_config import ClientConfig, fix_extensions

"""
These tests don't cover all aspects of this model.
Only added to accompany fix to a file extension issue.
"""


# Client config content but with no file validators specified
base_config = {
    "azure_client_id": "dummy-abcd-1234-5678",
    "azure_display_name": "test-config-details",
    "bucket_name": "sandy",
    "file_validators": []
    }


@pytest.mark.parametrize("extensions,expected", [([".csv"], ["csv"]),
                                                 (["csv"], ["csv"]),
                                                 ([".csv", ".xml"], ["csv", "xml"]),
                                                 ([".csv", ".xml", "zzz"], ["csv", "xml", "zzz"]),
                                                 ([".csv", ".abcdefghijk"], ["csv", "abcdefghijk"])
                                                 ]
                         )
def test_fix_extensions(extensions, expected):
    """Just checking that leading `.` removed from file extensions that have them"""
    result = fix_extensions(extensions)
    assert result == expected


def test_client_config():
    # ClientConfig needs json string but easier to construct content
    # using Python dict, then. use json.dumps
    config = base_config
    config["file_validators"].append({"name": "DisallowedFileExtensions",
                                     "validator_kwargs": {"extensions": [".exe", ".sh", ".bat", "ps"]}
                                      }
                                     )
    config["file_validators"].append({"name": "AllowedFileExtensions",
                                     "validator_kwargs": {"extensions": [".csv", ".xls", ".xlsx", "tsv"]}
                                      }
                                     )
    # Below is not a genuine validator type - should not be changed
    config["file_validators"].append({"name": "LostFileExtensions",
                                      "validator_kwargs": {"extensions": [".abc", ".zzz", "123"]}
                                      }
                                     )

    config_json = json.dumps(config)
    config = ClientConfig.model_validate_json(config_json)
    # DisallowedFileExtensions (1st) - leading dots removed
    assert config.file_validators[0].validator_kwargs["extensions"] == ["exe", "sh", "bat", "ps"]
    # AllowedFileExtensions (2nd) - leading dots removed
    assert config.file_validators[1].validator_kwargs["extensions"] == ["csv", "xls", "xlsx", "tsv"]
    # LostFileExtensions (3rd) [not a real one] - no change
    # This isn't actually a validator type - just demonstrating only the 2 types above are updated
    assert config.file_validators[2].validator_kwargs["extensions"] == [".abc", ".zzz", "123"]
