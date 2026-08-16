from src.ui.chrome import with_chrome
from src.ui.pages import research_chat

with_chrome(research_chat.render, "research_chat")()
