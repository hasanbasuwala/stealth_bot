from .commands import setup_commands
from .media import setup_media
from .callbacks import setup_callbacks

def setup_all_handlers(app):
    setup_commands(app)
    setup_media(app)
    setup_callbacks(app)
