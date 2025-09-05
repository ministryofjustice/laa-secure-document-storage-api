import os
import time
from io import BytesIO

import clamd
import structlog
from dotenv import load_dotenv

from src.models.status_report import ServiceObservations, Category
from src.utils.status_reporter import StatusReporter

load_dotenv()
logger = structlog.get_logger()


class ClamAVService:
    _instance = None

    def __init__(self):
        if ClamAVService._instance is not None:
            raise Exception("This class a singleton!")
        else:
            ClamAVService._instance = self
            _host = os.getenv('CLAMD_HOST', 'localhost')
            _port = int(os.getenv('CLAMD_PORT', '3310'))
            _clamd = clamd.ClamdNetworkSocket()
            _clamd.__init__(host=_host, port=_port, timeout=None)
            self._clamd = _clamd

    @staticmethod
    def get_instance():
        if ClamAVService._instance is None:
            ClamAVService()
        return ClamAVService._instance

    # documentation used for this https://docs.clamav.net/manual/Usage/Scanning.html
    async def check(self, file: BytesIO):
        status = 200
        response = {}
        start_time = time.time()
        scan_result = self._clamd.instream(file)
        if scan_result['stream'][0] == 'OK':
            message = 'file has no virus'
        elif scan_result['stream'][0] == 'FOUND':
            message = 'file has virus'
            status = 400
        else:
            message = 'Error occurred while processing'
            status = 500
        duration = time.time() - start_time
        logger.info(f"Virus scan took {duration:10.4f}s")

        response['message'] = message
        return response, status


async def virus_check(file: BytesIO):
    clamAv = ClamAVService.get_instance()
    return await clamAv.check(file)


class ClamAvServiceStatusReporter(StatusReporter):

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Reachable if the API is usable.
        Responding if the service responds to ping.
        """
        checks = ServiceObservations(label='antivirus')
        reachable, responding = checks.add_checks('reachable', 'responding')

        try:
            clam_av = ClamAVService.get_instance()
            # Check we can reach the API...
            clam_av._clamd.version()
            reachable.category = Category.success
            # ...and check we can reach the actual service
            clam_av._clamd.ping()
            responding.category = Category.success
        except Exception as e:
            logger.error(f'Status check {cls.label} failed: {e.__class__.__name__} {e}')
        return checks
