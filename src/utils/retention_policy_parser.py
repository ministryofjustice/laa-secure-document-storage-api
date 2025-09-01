from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def get_retention_expiry_date(retention_policy: str, start: datetime = None) -> datetime:

# Parse a string like '10y', '6m', '30d' and add that interval to the given start datetime 
# (which defaults to now if not provided as arg).
 
# Special cases:
# - 'DO NOT DELETE' -> raises error
# - 'UNKNOWN' -> raises error

# Parameter retention_policy: String must currently take the format of years ('y'), months ('m') or days ('d').
# The goal is to extend this in time to be more human readable (e.g '10 years' instead of '10y').

    return True
