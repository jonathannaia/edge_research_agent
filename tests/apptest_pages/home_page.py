from src.ui.chrome import with_chrome
from src.ui.pages import home

with_chrome(home.render, "home")()
