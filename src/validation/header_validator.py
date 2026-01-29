from typing import Tuple
from fastapi import Header


class HaveContentLengthInHeaders:
    # This could be dervived from an abstract base class in similar way to our file validators.
    # Not doing so for now to avoid boilerplate as we currently only have a single header validator.
    def validate(self, headers: Header, **kwargs) -> Tuple[int, str]:
        """
        Validate that requeast headers includes content-length value.
        """
        if headers.get('content-length') is not None:
            return 200, ""
        else:
            return 411, "content-length header not found"


def run_header_validators(headers: Header) -> Tuple[int, str]:
    validator = HaveContentLengthInHeaders()
    return validator.validate(headers)
