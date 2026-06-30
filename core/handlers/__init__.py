from .commands import setup_commands
# We will add media and callbacks in Phase 3.

def setup_all_handlers(app):
    setup_commands(app)
