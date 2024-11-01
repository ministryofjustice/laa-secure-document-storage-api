import os
from io import BytesIO

import clamd
from dotenv import load_dotenv

load_dotenv()


class AvCheckService:
    _instance = None

    def __init__(self):
        if AvCheckService._instance is not None:
            raise Exception("This class a singleton!")
        else:
            AvCheckService._instance = self
            _host = os.getenv('CLAMD_HOST', 'localhost')
            _port = int(os.getenv('CLAMD_PORT', '3310'))
            _clamd = clamd.ClamdNetworkSocket();
            _clamd.__init__(host=_host, port=_port, timeout=None)
            self._clamd = _clamd

    @staticmethod
    def get_instance():
        if AvCheckService._instance is None:
            AvCheckService()
        return AvCheckService._instance

    # documentation used for this https://docs.clamav.net/manual/Usage/Scanning.html
    async def check(self, file: BytesIO):
        status = 200
        response = {}
        scan_result = self._clamd.instream(file)
        if scan_result['stream'][0] == 'OK':
            message = 'file has no virus'
        elif scan_result['stream'][0] == 'FOUND':
            message = 'file has virus'
            status = 400
        else:
            message = 'Error occurred while processing'

        response['message'] = message
        return response, status


async def virus_check(file: BytesIO):
    clamAv = AvCheckService.get_instance()
    return await clamAv.check(file)