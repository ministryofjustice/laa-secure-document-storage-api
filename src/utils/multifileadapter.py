import os
import pathlib

import casbin
from casbin import load_policy_line
import structlog

logger = structlog.get_logger()


class MultiFileAdapter(casbin.FileAdapter):
    """
    Permits specifying a single file, or a directory within which all CSV files are retrieved.
    """
    def load_policy(self, model):
        if not os.path.exists(self._file_path):
            raise RuntimeError("invalid file path, file path cannot be empty")

        self._load_policy_file(model)

    def _load_policy_file(self, model):
        if os.path.isfile(self._file_path):
            logger.info(f"Loading policy from single file {self._file_path}")
            return super()._load_policy_file(model)

        candidates = [p for p in pathlib.Path(self._file_path).rglob("*.csv", case_sensitive=False)]
        for policy_path in candidates:
            logger.info(f"Loading policy from {policy_path}")
            with open(policy_path, "rb") as file:
                line = file.readline()
                while line:
                    load_policy_line(line.decode().strip(), model)
                    line = file.readline()
