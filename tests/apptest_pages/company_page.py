from src.ui.pages import company
from src.ui.ui import with_chrome

with_chrome(company.render, "company")()
