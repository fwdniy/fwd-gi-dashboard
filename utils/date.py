import calendar
from datetime import datetime

def get_ytd(date: datetime, dates: list[datetime]):
    ytd_date = datetime(date.year - 1, 12, 31)
    ytd_date = max([date for date in dates if date <= ytd_date]).date()

    return ytd_date

def get_qtd(date: datetime, dates: list[datetime]):
    qtd_months = [3, 6, 9, 12]

    qtd_month = max([month for month in qtd_months if month < date.month])

    if qtd_month == 12:
        qtd_date = datetime(date.year - 1, 12, 31)
    else:
        qtd_date = datetime(date.year, qtd_month, 1)
        qtd_date = get_last_day(qtd_date)

    qtd_date = max([date for date in dates if date <= qtd_date]).date()

    return qtd_date

def get_mtd(date: datetime, dates: list[datetime]):
    if (date.month == 1):
        mtd_date = datetime(date.year - 1, 12, 31)
    else:
        mtd_date = datetime(date.year, date.month - 1, 1)
        mtd_date = get_last_day(mtd_date)
    
    mtd_date = max([date for date in dates if date <= mtd_date]).date()

    return mtd_date

def get_last_day(date: datetime):
    date = datetime(date.year, date.month, calendar.monthrange(date.year, date.month)[1])

    return date