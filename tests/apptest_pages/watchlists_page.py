from src.ui.pages import watchlists
from src.ui.ui import with_chrome

with_chrome(watchlists.render, "watchlists")()
