from src.ui.chrome import with_chrome
from src.ui.pages import signal_board

with_chrome(signal_board.render)()
