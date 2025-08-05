from typing import List
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    """
    The supported outcomes for an observation.
    """
    failure = 'failure'
    success = 'success'


class CategoryObservation(BaseModel):
    """
    The result of a specific check, linking a phenomenon to an outcome.
    """
    phenomenon: str
    category: Category = Category.failure


class ServiceObservations(BaseModel):
    """
    The set of checks a service makes to verify its overall status.
    """
    label: str = 'service'
    observations: list[CategoryObservation] = Field(default_factory=list)

    def add_check(self, phenomenon: str) -> CategoryObservation:
        """
        Adds and returns a CategoryObservation with a default category of failure, thus allowing
        a set of observations to be prepared in a default 'failed' state and subsequently updated
        as the actual checks and tests are made.

        :param phenomenon:
        :return: CategoryObservation
        """
        obs = CategoryObservation(phenomenon=phenomenon)
        self.observations.append(obs)
        return obs

    def add_checks(self, *phenomena: str) -> List[CategoryObservation]:
        """
        Convenience method to add a sequence of named observations in a default 'failed' state.

        ```
        service_observations = ServiceObservations(label='my-service')
        present, active = service_observations.add_checks('present', 'active')
        ```

        :param phenomena: String names in the sequence they are to be created.
        :return:
        """
        observations = []
        for phenomenon in phenomena:
            observations.append(self.add_check(phenomenon=phenomenon))
        return observations

    def has_failures(self) -> bool:
        """
        Returns True if any observation has a category of failure.
        :return: bool
        """
        for scr in self.observations:
            if scr.category == Category.failure:
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
