import streamlit as st

from src.ui.chrome import NAV_ITEMS, render_top_nav
from src.ui.theme import inject_global_css

# Minimal stand-in Page objects (not real navigation) so render_top_nav's
# st.page_link calls have something valid to target — mirrors app.py's
# real pages dict shape without needing the actual page render functions.
st.session_state["_pages"] = {key: st.Page((lambda: None), title=label, url_path=key) for key, label in NAV_ITEMS}

inject_global_css()
render_top_nav("home")
