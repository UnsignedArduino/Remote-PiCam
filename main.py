import logging

import picamera

from create_logger import create_logger
from picam import NetworkPiCam

logger = create_logger(name=__name__, level=logging.DEBUG)

cam_name = "picam"
port = 7896

try:
    with picamera.PiCamera() as camera:
        camera.resolution = (720, 480)
        cam = NetworkPiCam(camera, cam_name, port)
        logger.debug("Attempting to connect")
        while not cam.connect(timeout=3):
            pass
        logger.info("Streaming images")
        while cam.is_connected:
            cam.send_image()
finally:
    logger.warning("Disconnecting")
