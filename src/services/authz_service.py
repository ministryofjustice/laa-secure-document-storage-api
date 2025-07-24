import os

import structlog
import casbin
from fastapi import HTTPException
from casbin.util.log import configure_logging

from src.models.status_report import ServiceObservations, Outcome
from src.utils.multifileadapter import MultiFileAdapter
from src.utils.status_reporter import StatusReporter

logger = structlog.get_logger()

DEFAULT_ACL_MODEL = casbin.Model()
DEFAULT_ACL_MODEL.load_model_from_text("""
[request_definition]
r = sub, obj, act
[policy_definition]
p = sub, obj, act
[policy_effect]
e = some(where (p.eft == allow))
[matchers]
m = r.sub == p.sub && r.obj == p.obj && regexMatch(r.act, p.act)
""")
DENY_ALL_POLICY = casbin.Adapter()


class AuthzService:
    """
    Singleton class to handle authorization checks, primarily a thin wrapper around a casbin Enforcer.
    """

    _instance = None
    _num_policies = 0

    def __new__(cls, enforcer: casbin.Enforcer | None = None):
        if cls._instance is None:
            cls._instance = super(AuthzService, cls).__new__(cls)
            if enforcer is None:
                policy = os.environ.get('CASBIN_POLICY', DENY_ALL_POLICY)
                if policy == DENY_ALL_POLICY:
                    logger.warning("No CASBIN_POLICY specified, using default deny-all policy")
                else:
                    policy = MultiFileAdapter(policy)
                # Use an Enforcer that will poll for changes to the specified model and policy files.
                enforcer = casbin.SyncedEnforcer(
                    model=os.environ.get('CASBIN_MODEL', DEFAULT_ACL_MODEL),
                    adapter=policy,
                )
                enforcer.start_auto_load_policy(int(os.getenv('CASBIN_RELOAD_INTERVAL', 600)))
                if os.getenv('LOGGING_LEVEL_CASBIN', 'NONE').upper() != 'NONE':
                    configure_logging()
                cls._num_policies = policy.num_files_processed
            cls._instance.enforcer = enforcer
        return cls._instance


def enforce(subj: str, obj: str, action: str) -> bool:
    """
    Convenience method passing through to the single casbin.Enforcer enforce method.

    :param subj: str
    :param obj: str
    :param action: str
    :return: bool
    """
    return AuthzService().enforcer.enforce(subj, obj, action)


def enforce_or_error(subj: str, obj: str, action: str, detail: str = 'Forbidden') -> None:
    """
    Convenience method passing through to the single casbin.Enforcer enforce method, but raises an HTTPException
    if the check fails.

    :param subj: str
    :param obj: str
    :param action: str
    :param detail: str
    :return: None
    """
    if not AuthzService().enforcer.enforce(subj, obj, action):
        logger.warning(f"User {subj} does not have {action} on {obj}")
        raise HTTPException(status_code=403, detail=detail)


class AuthzServiceStatusReporter(StatusReporter):
    label = 'authorisation'

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Present if a policy has been specified.
        Populated if policies have been loaded.
        """
        checks = ServiceObservations()
        present, populated = checks.add_checks('present', 'populated')

        if os.environ.get('CASBIN_POLICY', None) is not None:
            present.outcome = Outcome.success

        try:
            if AuthzService()._num_policies > 1:
                populated.outcome = Outcome.success
        except Exception as error:
            logger.error(f'Status check failed: {error.__class__.__name__} {error}')

        return checks
