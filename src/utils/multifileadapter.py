import os
import pathlib

import casbin
from casbin import load_policy_line
import structlog
from src.services.s3_client_config_service import s3_client_config_source

logger = structlog.get_logger()


class MultiFileAdapter(casbin.FileAdapter):
    """
    Permits specifying any combination of CSV files and directories containing CSV files from which policy lines are
    loaded. Multiple paths must be separated by a colon ':'
    """
    def load_policy(self, model):
        # Track the number of files processed to help with status reporting
        self.num_files_processed = 0
        # Do not check if path exists at this entry, because we may have been given a string with colon-separated paths
        self._load_policy_file(model)
        # New client config load from S3 - in addition to original policy load!
        self.load_policy_files_from_s3(model)

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
        self.num_files_processed = 0
        for pi, policy_path in enumerate(policy_file_paths):
            logger.info(f"> {pi} {policy_path}")

        for policy_path in policy_file_paths:
            try:
                with open(policy_path, "rb") as file:
                    line = file.readline()
                    while line:
                        load_policy_line(line.decode().strip(), model)
                        line = file.readline()
                    self.num_files_processed += 1
            except Exception as e:
                logger.error(f"Failed to load policy file {policy_path}: {e.__class__.__name__} {e}")
        logger.info(f"Processed {self.num_files_processed} policy files")

    def load_policy_files_from_s3(self, model):
        # For consistency using self.num_files_processed but wonder if this could just be local
        # variable instead?
        self.num_files_processed = 0
        s3_client_config_source.populate_filenames_if_old()
        s3_policy_file_paths = s3_client_config_source.csv_filenames
        for s3_policy_path in s3_policy_file_paths:
            try:
                lines = s3_client_config_source.get_file_lines(s3_policy_path)
                # unlike _load_policy_file, (maybe recklessly) using for loop instead of while
                for line in lines:
                    # Unlike file load, no decode method call as data is already str
                    load_policy_line(line.strip(), model)
                self.num_files_processed += 1
            except Exception as e:
                logger.error(f"Failed to load policy file from S3 {s3_policy_path}: {e.__class__.__name__} {e}")
        logger.info(f"Processed {self.num_files_processed} policy files from S3")
