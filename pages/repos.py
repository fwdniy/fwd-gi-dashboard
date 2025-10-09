from interface import initialize
from pages.repos import build_filters, load_data, build_chart

initialize()

build_filters()

df = load_data()

build_chart(df)