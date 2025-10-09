import streamlit as st
from interface import initialize
from pages.users import get_permissions, build_grid, build_form, edit_data

initialize()

df = get_permissions()

grid = build_grid(df)

build_form(df)

edit_data(grid, df)