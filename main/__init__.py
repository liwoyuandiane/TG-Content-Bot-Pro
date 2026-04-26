"""旧版初始化文件，已迁移到 app.py"""
# This file is kept for backward compatibility but most functionality has been moved to app.py
# New code should use the modern structure with app.py as the entry point

# Import core components for backward compatibility
from .core.clients import client_manager
from .core.database import db_manager
from .config import settings

# For backward compatibility with plugins that might import directly from here
# These will be deprecated in future versions
API_ID = settings.API_ID if hasattr(settings, 'API_ID') else None
API_HASH = settings.API_HASH if hasattr(settings, 'API_HASH') else None
BOT_TOKEN = settings.BOT_TOKEN if hasattr(settings, 'BOT_TOKEN') else None
SESSION = settings.SESSION if hasattr(settings, 'SESSION') else None
AUTH = settings.AUTH if hasattr(settings, 'AUTH') else None
FORCESUB = settings.FORCESUB if hasattr(settings, 'FORCESUB') else None