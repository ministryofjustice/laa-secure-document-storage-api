import os

import structlog
import casbin
from casbin.util.log import configure_logging

logger = structlog.get_logger()


class AuthzServiceSingleton:
    """
    Singleton class to handle authorization checks, primarily a thin wrapper around a casbin Enforcer.
    """

    _instance = None

    def __new__(cls, enforcer: casbin.Enforcer|None = None):
        if cls._instance is None:
            cls._instance = super(AuthzServiceSingleton, cls).__new__(cls)
            if enforcer is None:
                # Use an Enforcer that will poll for changes to the specified model and policy files.
                enforcer = casbin.SyncedEnforcer(
                    model=os.environ.get('CASBIN_MODEL', '../authz/any_authenticated_access.conf'),
                    adapter=os.environ.get('CASBIN_POLICY', '../authz/any_authenticated_access.csv'),
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
