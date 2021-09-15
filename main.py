import logging
from json import loads as load_json, dumps as dump_json
from pathlib import Path

import picamera
from create_logger import create_logger
from picam import NetworkPiCam

logger = create_logger(name=__name__, level=logging.DEBUG)

SETTINGS_PATH = Path.cwd() / "settings.json"

defaults = {
    "camera": {
        "name": "picam",
        "port": 7896
    },
    "pan_tilt": {
        "enable": True
    }
}

logger.debug(f"Loading settings from {SETTINGS_PATH}")
if not SETTINGS_PATH.exists():
    logger.warning("Settings file does not exist, creating!")
    SETTINGS_PATH.write_text(dump_json(defaults, indent=4))
settings = {**defaults, **load_json(SETTINGS_PATH.read_text())}

try:
    with picamera.PiCamera() as camera:
        camera.resolution = (720, 480)
        cam = NetworkPiCam(camera, settings["camera"]["name"],
                           settings["camera"]["port"])
        logger.debug("Attempting to connect")
        while not cam.connect(timeout=3):
            pass
        logger.info("Streaming images")
        while cam.is_connected:
            cam.send_image()
            cam.service_settings()
finally:
    logger.warning("Disconnecting")
