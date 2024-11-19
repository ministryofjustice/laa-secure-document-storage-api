from fastapi import Response


class ValidationResponse(Response):
    def __init__(self, status_code, message=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if message is None:
            message = []
        self.status_code = status_code
        self.message = message
