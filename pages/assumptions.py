import streamlit as st
from interface import initialize
from pages.assumptions import get_data, map_data, build_filters, build_grid

class AssumptionsConfig:
    CATEGORY = None
    SUBCATEGORY = None
    TENOR = None
    UNIT = None
    INDEX = None
    METRICS = None
    METRIC_VALUES = None
    LBU = None
    RATINGS = None
    USERS = None

initialize()

get_data(AssumptionsConfig)

map_data(AssumptionsConfig)

build_filters(AssumptionsConfig)

build_grid(AssumptionsConfig)