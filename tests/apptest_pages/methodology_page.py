from src.ui.chrome import with_chrome
from src.ui.pages import methodology

with_chrome(methodology.render, "methodology")()
