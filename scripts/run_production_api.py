"""Start the hardened UIIP FastAPI service with Uvicorn."""

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.live_security import LiveSecuritySettings, install_live_security

settings = HTTPServiceSettings.from_environment()
app = create_http_app(settings)
install_live_security(app, LiveSecuritySettings.from_environment())
uvicorn.run(app, host=os.getenv("UIIP_HTTP_HOST", "127.0.0.1"), port=int(os.getenv("UIIP_HTTP_PORT", "8000")))
