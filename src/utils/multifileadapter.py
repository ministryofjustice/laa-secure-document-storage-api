import os
import pathlib

import casbin
from casbin import load_policy_line
import structlog

logger = structlog.get_logger()


class MultiFileAdapter(casbin.FileAdapter):
    """
    Permits specifying any combination of CSV files and directories containing CSV files from which policy lines are
    loaded. Multiple paths must be separated by a colon ':'
    """
    def load_policy(self, model):
        # Do not check if path exists at this entry, because we may have been given a string with colon-separated paths
        self._load_policy_file(model)

    def _load_policy_file(self, model):
        # List of policy files to be used for loading
        policy_file_paths = []
        # We may receive a Path or a string in _file_path, but we will only get multiples in a str.
        # So here we ensure we are always processing a list of strings.
        if isinstance(self._file_path, str):
            # Combined paths may need to be quoted, so also strip those here
            candidate_paths = [c.strip("'").strip('"') for c in self._file_path.split(':')]
        else:
            candidate_paths = [self._file_path, ]
        for candidate in candidate_paths:
            if os.path.isfile(candidate) and os.path.splitext(candidate)[1].lower() == '.csv':
                # Candidate is a CSV file
                policy_file_paths.append(candidate)
            elif os.path.isdir(candidate):
                # Candidate is a directory, so search for all CSV files within
                # Case-insensitive extension in rglob: To be replaced with `case_sensitive=False` from Python 3.12
                policy_file_paths.extend([p for p in pathlib.Path(candidate).rglob("*.[Cc][Ss][Vv]")])
            else:
                # Candidate was not an existing CSV file or a directory, so log an error and continue
                logger.error(f"Specified path {candidate} does not exist or is not a CSV file")
                continue

        # Load policy lines from each of the found file paths
        for policy_path in policy_file_paths:
            logger.info(f"Loading policy from {policy_path}")
            with open(policy_path, "rb") as file:
                line = file.readline()
                while line:
                    load_policy_line(line.decode().strip(), model)
                    line = file.readline()
