class ValidationResponse:
    def __init__(self, status_code, message=None):
        if message is None:
            message = []
        self.status_code = status_code
        self.message = message
