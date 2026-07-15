import os
import datetime
import boto3
import structlog

logger = structlog.get_logger()


class S3ClientConfigService:
    """
    Gets client config filenames and files from client config S3 bucket.
    Because these files only change from time-to-time, the details are held within the following
    attributes:
        self.filenames - all filenames
        self.csv_filenames - csv filenames only
        self.json_filenames - json filenames only

    To refresh these details call the populate_filenames method. This will run automatically
    when instance created if auto_populate parameter is True.

    Note this only creates a temporary S3 client each time bucket accessed. Could change,
    not sure what difference this makes - is there a constant connection otherwise? As
    client is presumably sending requests behind the scenes, maybe not?
    """
    def __init__(self, auto_populate: bool = True):
        self.bucket = os.getenv("CLIENT_CONFIG_BUCKET_NAME", "sds-client-configs")
        self.filenames = []
        self.csv_filenames = []
        self.json_filenames = []
        self.last_refresh_time: datetime.datetime | None = None
        if auto_populate:
            self.populate_filenames()

    def get_s3_client(self):
        # This duplicates S3Serivce.get_s3_client class method
        # Could change this to a free-standing function shared by both classes
        # but keeping separate for now to avoid disruption to existing functionality
        # (alternatively could go for inheritance-based approach but that might overcomplicate things)
        s3_client = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'eu-west-2'),
            aws_access_key_id=os.getenv('AWS_KEY_ID', ''),
            aws_secret_access_key=os.getenv('AWS_KEY', ''),
            endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
            )
        return s3_client

    def get_details_of_files(self, max_calls: int = 3, max_keys: int = 1000) -> list[dict]:
        s3_client = self.get_s3_client()
        all_file_details = []
        continuation_token: str | None = None
        # Need to iterate because there is a maximum number of files that can be returned in one
        # list_objects_v2 call. Default is 1000 which should be enough, but just in case.
        for _ in range(max_calls):
            if not continuation_token:
                returned_file_details = s3_client.list_objects_v2(Bucket=self.bucket, MaxKeys=max_keys)
            else:
                returned_file_details = s3_client.list_objects_v2(Bucket=self.bucket, MaxKeys=max_keys,
                                                                  ContinuationToken=continuation_token)
            all_file_details.append(returned_file_details)
            # Can stop iteration if returned details NOT truncated (so we must have all)
            if returned_file_details.get("IsTruncated", False) is False:
                break
            else:
                continuation_token = returned_file_details.get("NextContinuationToken")
        s3_client.close()
        return all_file_details

    def polulate_filenames_if_old(self, waitfor: datetime.timedelta = datetime.timedelta(hours=1)):
        """
        Refresh the filenames if either there's no last_refresh_time or the last_refresh_time was
        more than a specified interval in the past (defaults to 1 hour)
        """
        if not self.last_refresh_time or datetime.datetime.now() - self.last_refresh_time > waitfor:
            self.populate_filenames()
            logger.info("S3 client-config filenames refreshed")
        else:
            logger.info(f"S3 client-config filenames not refreshed as last was too recent: {self.last_refresh_time}")

    def populate_filenames(self):
        self.filenames = []
        file_details: list[dict] = self.get_details_of_files()
        for file_collection in file_details:
            contents = file_collection.get("Contents", [])
            self.filenames.extend([c.get("Key") for c in contents])
        # If final file collection has "IsTruncated" True, then we don't have complete set of details
        truncation_flag = file_collection.get("IsTruncated", False)
        if truncation_flag:
            logger.warning("Config file read from S3 failed to read all the files. Could be too many files.")
        self.csv_filenames = [f for f in self.filenames if f.lower().endswith(".csv")]
        self.json_filenames = [f for f in self.filenames if f.lower().endswith(".json")]
        self.last_refresh_time = datetime.datetime.now()

    def get_file(self, key: str) -> str:
        """
        Return specified file content as string. Presumably should be
        fine as we're only expecting to read csv and json, not binary.
        """
        s3_client = self.get_s3_client()
        # Could change things so we check file is in self.filenames
        # before atttempting to read it.
        try:
            file_object: dict = s3_client.get_object(Bucket=self.bucket, Key=key)
            file_content = file_object.get("Body").read().decode("utf-8")
        except Exception as exc:
            logger.error(f"Failed to read config file {key}: {exc}")
            file_content = ""
        finally:
            s3_client.close()
        return file_content

    def get_file_lines(self, key: str) -> list[str]:
        """
        Return specified file content as list of line-by-line strings.
        """
        content = self.get_file(key)
        return content.splitlines()


# Simpler than creating singleton-class? Just create instance that's available for import.
s3_client_config_source = S3ClientConfigService()
