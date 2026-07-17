from datetime import timedelta
def add_business_days(start, days):
    d=start
    remaining=days
    while remaining:
        d += timedelta(days=1)
        if d.weekday()<5:
            remaining-=1
    return d
