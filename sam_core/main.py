"""
Sam Core Daemon Entrypoint.
Starts the server, event bus, and core subsystems.
Fails clearly if configuration is invalid.
"""
import sys

import uvicorn
from pydantic import ValidationError

try:
    from sam_core.config import settings
except ValidationError as val_err:
    sys.stderr.write("====================================================\n")
    sys.stderr.write("CONFIGURATION ERROR: Sam Core failed to start.\n")
    sys.stderr.write("====================================================\n")
    for err in val_err.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "")
        sys.stderr.write(f"  Field: {field}\n  Error: {msg}\n\n")
    sys.stderr.write("Please check your .env configuration file.\n")
    sys.exit(1)

from sam_core.logger import get_logger, setup_logging

logger = get_logger("main")


def start():
    """Launch Sam Core daemon with Uvicorn."""
    setup_logging(level=settings.log_level, logs_dir=settings.logs_dir)
    logger.info("==================================================")
    logger.info(f"  Starting {settings.app_name} Assistant Core Daemon")
    logger.info(f"  Version     : {settings.version}")
    logger.info(f"  Environment : {settings.environment}")
    logger.info(f"  Host/Port   : {settings.host}:{settings.port}")
    logger.info(f"  WebSocket   : {settings.ws_path}")
    logger.info(f"  Data Dir    : {settings.data_dir}")
    logger.info("==================================================")

    try:
        uvicorn.run(
            "sam_core.api.server:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
        )
    except Exception as exc:
        logger.error(f"Fatal error starting Sam Core: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    start()
