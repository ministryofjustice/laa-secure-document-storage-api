import structlog

from src.utils.status_reporter import StatusReporter
from src.models.status_report import StatusReport, ServiceObservations

logger = structlog.get_logger()


async def get_status() -> StatusReport:
    """
    Runs all available StatusReporters and returns a StatusReport with all outcomes.
    """
    status = StatusReport()
    for reporter in StatusReporter.__subclasses__():
        try:
            status.services[reporter.label] = reporter.get_status()
        except Exception as error:
            logger.error(f'Error gathering {reporter.__class__.__name__} status {error.__class__.__name__} {error}')
            # Add a report for the failure to get a report
            so = ServiceObservations()
            so.add_check('generation')  # Default outcome is `failure`
            status.services[reporter.__class__.__name__] = so
    return status
