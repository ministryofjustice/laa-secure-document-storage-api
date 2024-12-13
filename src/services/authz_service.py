import os

import structlog
import casbin
from casbin.util.log import configure_logging

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

    def __new__(cls, enforcer: casbin.Enforcer | None = None):
        if cls._instance is None:
            cls._instance = super(AuthzService, cls).__new__(cls)
            if enforcer is None:
                policy = os.environ.get('CASBIN_POLICY', DENY_ALL_POLICY)
                if policy == DENY_ALL_POLICY:
                    logger.warning(f"No CASBIN_POLICY specified, using default deny-all policy")
                else:
                    logger.info(f"Using policy {policy}")
                # Use an Enforcer that will poll for changes to the specified model and policy files.
                enforcer = casbin.SyncedEnforcer(
                    model=os.environ.get('CASBIN_MODEL', DEFAULT_ACL_MODEL),
                    adapter=policy,
                )
                enforcer.start_auto_load_policy(int(os.getenv('CASBIN_RELOAD_INTERVAL', 600)))
                if os.getenv('LOGGING_LEVEL_CASBIN', 'NONE').upper() != 'NONE':
                    configure_logging()
            cls._instance.enforcer = enforcer
        return cls._instance

    def check_permission(self, subj: str, obj: str, action: str) -> bool:
        """
        Check if a subject has permission to perform the specified action on a resource.

        :param subj: str
        :param obj: str
        :param action: str
        :return: bool
        """
        return self.enforcer.enforce(subj, obj, action)
