from src.ui.pages import research
from src.ui.ui import with_chrome

with_chrome(research.render, "research")()
