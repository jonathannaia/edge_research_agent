import streamlit as st

from src.ui.chrome import render_brand_header, render_sidebar_status
from src.ui.theme import inject_global_css

inject_global_css()
with st.sidebar:
    render_brand_header()
    render_sidebar_status()
