from src.ui.chrome import with_chrome
from src.ui.pages import capital_rotation

with_chrome(capital_rotation.render, "capital_rotation")()
