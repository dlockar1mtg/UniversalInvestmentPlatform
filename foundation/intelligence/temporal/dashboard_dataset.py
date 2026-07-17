from .horizon_registry import HorizonRegistry
def export_rows():
    rows=[]
    for h,info in HorizonRegistry.all().items():
        rows.append({"horizon":h.value,"calendar_days":info.calendar_days,
        "business_days":info.business_days,"trading_days":info.trading_days,
        "months":info.months})
    return rows
