from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class RetentionPolicyError(ValueError):
    """ 
    RetentionPolicyError is raised when retention period is DO NOT DELETE or UNKNOWN 
    """
    pass

def get_retention_expiry_date(retention_policy: str, start: datetime = None) -> datetime:

    """
    Parses a string like '10y', '6m', '30d' and adds that interval to the given start datetime 
    (which defaults to now if not provided as arg).
    
    Special cases:
    - 'DO NOT DELETE' -> raises error
    - 'UNKNOWN' -> raises error

    Parameter retention_policy: String must currently take the format of years ('y'), months ('m') or days ('d').
    The goal is to extend this in time to be more human readable (e.g '10 years' instead of '10y').
    """

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
