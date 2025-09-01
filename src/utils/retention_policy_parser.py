from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class RetentionPolicyError(ValueError):
    """ RetentionPolicyError is raised when retention period is DO NOT DELETE or UNKNOWN. """
    pass

class InvalidRetentionFormatError(ValueError):
    """Raised when the retention policy format is invalid (e.g., wrong unit or malformed string)."""
    pass


def get_retention_expiry_date(retention_policy: str, start: datetime = None) -> datetime:

    
    """
    Calculates the expiry date based on a retention policy string and a start date.

    The retention policy should be in the format of '10y', '6m', or '30d', where:
    - 'y' stands for years
    - 'm' stands for months
    - 'd' stands for days

    Special cases:
    - 'DO NOT DELETE' or 'UNKNOWN' will raise RetentionPolicyError.

    Args:
        retention_policy (str): The retention policy string.
        start (datetime, optional): The start date from which to calculate the expiry.
        Defaults to the current datetime if not provided.

    Returns:
        datetime: The calculated expiry date.

    Raises:
        RetentionPolicyError: If the policy is 'DO NOT DELETE' or 'UNKNOWN'.
        InvalidRetentionFormatError: If the format is invalid (e.g., wrong unit).
    """


    normalised = retention_policy.strip().upper()
    if normalised in {"DO NOT DELETE", "UNKNOWN"}:
        raise RetentionPolicyError(f"Invalid retention policy: {retention_policy}")

    if start is None:
        start = datetime.now()

    unit = retention_policy[-1].lower()

    try:
        value = int(retention_policy[:-1])
    except ValueError:
        raise ValueError("Invalid number in input string")
    
    # calculate retention expiry date by adding retention_policy delta to start date.
    # relativedelta from dateutil library correctly accounts for leap years.
        
    if unit not in {'y', 'm', 'd'}:
        raise InvalidRetentionFormatError(f"Invalid unit in retention policy: '{unit}'. Must have format 'y', 'm', or 'd'.")
    if unit == "y":
        return start + relativedelta(years=value)
    if unit == "m":
        return start + relativedelta(months=value)
    if unit == "d":
        return start + relativedelta(days=value)
