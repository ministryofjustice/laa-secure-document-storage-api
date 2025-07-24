import structlog

from src.utils.status_reporter import StatusReporter
from src.models.status_report import StatusReport

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
            logger.info(f'Error gathering {reporter.__class__.__name__} status {error.__class__.__name__} {error}')
    return status
