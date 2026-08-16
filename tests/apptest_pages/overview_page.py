from src.ui.chrome import with_chrome
from src.ui.pages import overview

with_chrome(overview.render, "overview")()
