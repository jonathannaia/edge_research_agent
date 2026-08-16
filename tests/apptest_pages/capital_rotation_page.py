from src.ui.pages import capital_rotation
from src.ui.ui import with_chrome

with_chrome(capital_rotation.render, "capital_rotation")()
