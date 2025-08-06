from src.models.status_report import ServiceObservations


class StatusReporter:
    """
    Implemented in components whose state or behaviour can be configured, to enable reporting of the health or status
    of the component, and hence also the parent service.

    Subclasses of this are gathered and used for status reporting of the overall service.
    """
    # Used in the human-readable status report
    label = 'status'

    @classmethod
    def get_status(cls) -> ServiceObservations:
        raise NotImplementedError()
