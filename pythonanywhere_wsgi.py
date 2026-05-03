import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_HOME = Path("/home/digitallife11/Carpool-and-Resort-Pooling-2025")

if str(PROJECT_HOME) not in sys.path:
    sys.path.insert(0, str(PROJECT_HOME))

load_dotenv(PROJECT_HOME / ".env", override=False)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webSchedule.settings")

from django.core.wsgi import get_wsgi_application


application = get_wsgi_application()