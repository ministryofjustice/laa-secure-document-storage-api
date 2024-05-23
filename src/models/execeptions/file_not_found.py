class FileNotFoundException(Exception):
    def __init__(self, message, filename):
        self.message = message
        self.filename = filename
        super().__init__(message)
