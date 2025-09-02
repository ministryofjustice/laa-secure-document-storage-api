from datetime import datetime
from dateutil.relativedelta import relativedelta


class DoNotDeleteRetentionError(ValueError):
    """Raised when the retention policy is 'DO NOT DELETE', indicating the file should never be deleted."""
    pass


class UnknownRetentionPolicyError(ValueError):
    """Raised when the retention policy is 'UNKNOWN', indicating missing or undefined retention information."""
    pass


class InvalidRetentionFormatError(ValueError):
    """Raised when the retention policy format is invalid (e.g., wrong unit or malformed string)."""
    pass


def get_retention_expiry_date(retention_policy: str, start: datetime = None) -> datetime:

    """
    Calculates the expiry date based on a retention policy and a start date.

    The retention policy should be in the format of '10y', '6m', or '30d', where:
        - 'y' stands for years
        - 'm' stands for months
        - 'd' stands for days
        - The preceding numerical value must be a positive integer.
        - You cannot currently mix units (e.g. '10y6m' is not valid).

    Special cases:
        - 'DO NOT DELETE': A valid retention policy indicating the file should never be deleted. Raises DoNotDeleteRetentionError.
        - 'UNKNOWN': An invalid retention policy indicating missing or undefined retention. Raises UnknownRetentionPolicyError.


    Args:
        retention_policy (str): The retention policy string, representing a positive integer number of days, months or years. 
        start (datetime, optional): The start date from which to calculate the expiry.
        Defaults to the current datetime if not provided (datetime.now()).

    Returns:
        datetime: The calculated expiry date.

    Raises:
        DoNotDeleteRetentionError: If the policy is 'DO NOT DELETE'.
        UnknownRetentionPolicyError: If the policy is 'UNKNOWN'.
        InvalidRetentionFormatError: If the format is invalid (e.g., wrong unit).
        ValueError: If the numeric part of the policy is not a valid integer.

    """

    normalised = retention_policy.strip().upper()
    if normalised == "DO NOT DELETE":
        raise DoNotDeleteRetentionError("File is marked as DO NOT DELETE and should not be expired.")
    elif normalised == "UNKNOWN":
        raise UnknownRetentionPolicyError("Retention policy is UNKNOWN and must be defined")

    if start is None:
        start = datetime.now()

    unit = retention_policy[-1].lower()

    try:
        value = int(retention_policy[:-1])
        if value < 0:
            raise ValueError("Retention period cannot be negative.")
    except ValueError:
        raise ValueError("Invalid number in input string")

    # calculate retention expiry date by adding retention_policy delta to start date.
    # relativedelta from dateutil library correctly accounts for leap years.

    if unit not in {'y', 'm', 'd'}:
        raise InvalidRetentionFormatError(
            f"Invalid unit in retention policy: '{unit}'. "
            "Must have format 'y', 'm', or 'd'.")

    if unit == "y":
        return start + relativedelta(years=value)
    if unit == "m":
        return start + relativedelta(months=value)
    if unit == "d":
        return start + relativedelta(days=value)
