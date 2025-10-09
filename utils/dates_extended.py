import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def get_ytd(date: datetime, dates: list[datetime]) -> datetime.date:
    ytd_date = datetime(date.year - 1, 12, 31)
    ytd_date = max([date for date in dates if date <= ytd_date]).date()
    
    return ytd_date

def get_qtd(date: datetime, dates: list[datetime]) -> datetime.date:
    qtd_months = [3, 6, 9, 12]
    
    qtd_month = max([month for month in qtd_months if month < date.month or date.month <= min(qtd_months) and month == max(qtd_months)])

    if qtd_month == 12:
        qtd_date = datetime(date.year - 1, 12, 31)
    else:
        qtd_date = datetime(date.year, qtd_month, 1)
        qtd_date = get_last_day(qtd_date)

    qtd_date = max([date for date in dates if date <= qtd_date]).date()

    return qtd_date

def get_mtd(date: datetime, dates: list[datetime]) -> datetime.date:
    if (date.month == 1):
        mtd_date = datetime(date.year - 1, 12, 31)
    else:
        mtd_date = datetime(date.year, date.month - 1, 1)
        mtd_date = get_last_day(mtd_date)
    
    mtd_date = max([date for date in dates if date <= mtd_date]).date()

    return mtd_date

def get_last_day(date: datetime) -> datetime.date:
    date_last_day = datetime(date.year, date.month, calendar.monthrange(date.year, date.month)[1])

    return date_last_day

def get_one_day(date: datetime, dates: list[datetime]) -> datetime.date:
    date_1d = date - timedelta(days=1)
    date_1d = datetime(date_1d.year, date_1d.month, date_1d.day)
    date_1d = max([date for date in dates if date <= date_1d]).date()

    return date_1d

def get_one_week(date: datetime, dates: list[datetime]) -> datetime.date:
    date_1w = date - timedelta(weeks=1)
    date_1w = datetime(date_1w.year, date_1w.month, date_1w.day)
    date_1w = max([date for date in dates if date <= date_1w]).date()

    return date_1w

def get_one_month(date: datetime, dates: list[datetime]) -> datetime.date:
    date_1m = date - relativedelta(months=1)
    date_1m = datetime(date_1m.year, date_1m.month, date_1m.day)
    date_1m = max([date for date in dates if date <= date_1m]).date()
    
    return date_1m