from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class RetentionPolicyError(ValueError):
    """ 
    RetentionPolicyError is raised when retention period is DO NOT DELETE or UNKNOWN 
    """
    pass

def get_retention_expiry_date(retention_policy: str, start: datetime = None) -> datetime:

    """
    Parses a string like '10y', '6m', '30d' and adds that time interval to the given start datetime, returning an expiry date.

    Param `retention_policy` must take the format of 'y', 'm' or 'd', representing years, months, days respectively.
    The goal is to extend this in time to be more human readable (e.g. accept '10 years' instead of just '10y').
    
    Param `start` is optional and defaults to NOW if not provided.

    Special cases:
    - 'DO NOT DELETE' -> raises RetentionPolicyError
    - 'UNKNOWN' -> raises RetentionPolicyError

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
        
    if unit == "y":
        return start + relativedelta(years=value)
    elif unit == "m":
        return start + relativedelta(months=value)
    elif unit == "d":
        return start + relativedelta(days=value)
    else:
        raise ValueError("Invalid format: retention policy must end with 'y' (years), 'm' (months) or 'd' (days)")
