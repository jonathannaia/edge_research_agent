from src.ui.chrome import with_chrome
from src.ui.pages import watchlists

with_chrome(watchlists.render)()
