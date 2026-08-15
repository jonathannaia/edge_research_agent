from src.ui.chrome import with_chrome
from src.ui.pages import ticker_detail

with_chrome(ticker_detail.render)()
