from typing import List
from enum import Enum

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    """
    The supported outcome values.
    Outcome
    """
    failure = 'failure'
    success = 'success'


class Observation(BaseModel):
    """
    The result of a specific check, linking a phenomenon to an outcome.
    Observation
    """
    name: str
    outcome: Outcome = Outcome.failure


class ServiceObservations(BaseModel):
    """
    The set of checks a service makes to verify its overall status.
    ServiceObservations
    """
    label: str = 'service'
    checks: list[Observation] = Field(default_factory=list)

    def add_check(self, name: str) -> Observation:
        """
        Adds and returns a StatusCheckResult with a default outcome of failure, thus allowing
        a set of checks to be prepared in a default 'failed' state and subsequently updated
        as the actual checks and tests are made.

        :param name:
        :return: StatusCheckResult
        """
        obs = Observation(name=name)
        self.checks.append(obs)
        return obs

    def add_checks(self, *names: str) -> List[Observation]:
        """
        Convenience method to add a sequence of named checks in a default 'failed' state.

        ```
        service_checks = ServiceChecks()
        present, active = service_checks('present', 'active')
        ```

        :param names: String names in the sequence they are to be created.
        :return:
        """
        observations = []
        for name in names:
            observations.append(self.add_check(name=name))
        return observations

    def has_failures(self) -> bool:
        """
        Returns True if any outcome is a failure.
        :return: bool
        """
        for scr in self.checks:
            if scr.outcome == Outcome.failure:
                return True
        return False


class StatusReport(BaseModel):
    """
    All the service checks combined into a single status report.
    """
    services: List[ServiceObservations] = Field(default_factory=list)

    def has_failures(self) -> bool:
        for so in self.services:
            if so.has_failures():
                return True
        return False
