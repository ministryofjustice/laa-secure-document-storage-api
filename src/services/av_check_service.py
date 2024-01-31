from io import BytesIO

import clamd


class AvCheckService:
    _instance = None

    def __init__(self):
        if AvCheckService._instance is not None:
            raise Exception("This class a singleton!")
        else:
            AvCheckService._instance = self
            _clamd = clamd.ClamdNetworkSocket();
            _clamd.__init__(host='localhost', port=3310, timeout=None)
            self._clamd = _clamd

    @staticmethod
    def get_instance():
        if AvCheckService._instance is None:
            AvCheckService()
        return AvCheckService._instance

# documentation used for this https://docs.clamav.net/manual/Usage/Scanning.html
    def check(self, file: BytesIO):
        status = 200
        response = {}
        scan_result = self._clamd.instream(file)
        if scan_result['stream'][0] == 'OK':
            message = 'file has no virus'
        elif scan_result['stream'][0] == 'FOUND':
            message = 'file has virus'
            print(scan_result)
        else:
            message = 'Error occurred while processing'

        response['message'] = message
        return response, status
