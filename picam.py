import logging
import struct
from io import BytesIO
from socket import socket
from typing import Union

import networkzero as nw0
from PIL import Image

from create_logger import create_logger
from PCA9685 import PCA9685
import picamera

logger = create_logger(name=__name__, level=logging.DEBUG)


class NetworkPiCam:
    """
    A class to manage connecting and sending images as a PiCam.
    """

    def __init__(self, cam: picamera, cam_name: str, port: int,
                 pan_tilt: bool = True):
        """
        Initiate the PiCam. This does not actually connect to the PiCam until
        you call connect().

        :param cam: The PiCamera object.
        :param cam_name: The name of the PiCamera. This is used by the other
         end to discover the camera.
        :param port: The port to connect to
        :param pan_tilt: Whether to pan/tilt or not. Defaults to True.
        """
        self._cam = cam
        self._cam_name = cam_name
        self._port = port
        self._pan_tilting = pan_tilt
        if not self._pan_tilting:
            logger.warning("Not using pan/tilt!")
        self._client_socket = None
        self._server_address = None
        self._connection = None
        self._driver = None
        self._connected = False
        self.settings = {
            "awb_mode": {
                "selected": "auto",
                "available": [
                    "off",
                    "auto",
                    "sunlight",
                    "cloudy",
                    "shade",
                    "tungsten",
                    "fluorescent",
                    "incandescent",
                    "flash",
                    "horizon"
                ]
            },
            "brightness": {
                "min": 0,
                "max": 100,
                "value": 50
            },
            "contrast": {
                "min": -100,
                "max": 100,
                "value": 0
            },
            "effect": {
                "selected": "none",
                "available": [
                    "none",
                    "negative",
                    "solarize",
                    "sketch",
                    "denoise",
                    "emboss",
                    "oilpaint",
                    "hatch",
                    "gpen",
                    "pastel",
                    "watercolor",
                    "film",
                    "blur",
                    "saturation",
                    "colorswap",
                    "washedout",
                    "posterise",
                    "colorpoint",
                    "colorbalance",
                    "cartoon",
                    "deinterlace1",
                    "deinterlace2"
                ]
            },
            "iso": {
                "selected": 0,
                "available": [
                    0,
                    100,
                    200,
                    320,
                    400,
                    500,
                    640,
                    800
                ]
            },
            "resolution": {
                "selected": (720, 480),
                "available": [
                    "128x96",
                    "160x120",
                    "160x144",
                    "176x144",
                    "180x132",
                    "180x135",
                    "192x144",
                    "234x60",
                    "256x192",
                    "320x200",
                    "320x240",
                    "320x288",
                    "320x400",
                    "352x288",
                    "352x240",
                    "384x256",
                    "384x288",
                    "392x72",
                    "400x300",
                    "460x55",
                    "480x320",
                    "468x32",
                    "468x60",
                    "512x342",
                    "512x384",
                    "544x372",
                    "640x350",
                    "640x480",
                    "640x576",
                    "704x576",
                    "720x350",
                    "720x400",
                    "720x480",
                    "720x483",
                    "720x484",
                    "720x486",
                    "720x540",
                    "720x576",
                    "729x348",
                    "768x576",
                    "800x600",
                    "832x624",
                    "856x480",
                    "896x600",
                    "960x720",
                    "1024x576",
                    "1024x768",
                    "1080x720",
                    "1152x768",
                    "1152x864",
                    "1152x870",
                    "1152x900",
                    "1280x720",
                    "1280x800",
                    "1280x854",
                    "1280x960",
                    "1280x992",
                    "1280x1024",
                    "1360x766",
                    "1365x768",
                    "1366x768",
                    "1365x1024",
                    "1400x788",
                    "1400x1050",
                    "1440x900",
                    "1520x856",
                    "1536x1536",
                    "1600x900",
                    "1600x1024",
                    "1600x1200",
                    "1792x1120",
                    "1792x1344",
                    "1824x1128",
                    "1824x1368",
                    "1856x1392",
                    "1920x1080",
                    "1920x1200",
                    "1920x1440",
                    "2000x1280",
                    "2048x1152",
                    "2048x1536",
                    "2048x2048",
                    "2500x1340",
                    "2560x1600",
                    "3072x2252",
                    "3600x2400"
                ]
            },
            "saturation": {
                "min": -100,
                "max": 100,
                "value": 0
            },
            "servos": {
                "enable": self._pan_tilting,
                "pan": {
                    "min": 0,
                    "max": 180,
                    "value": 90
                },
                "tilt": {
                    "min": 0,
                    "max": 60,
                    "value": 30
                }
            }
        }

    def connect(self, timeout: int = 30) -> bool:
        """
        Actually connect to the server.

        :param timeout: Wait up to x amount of seconds before giving up.
        :return: A bool on whether we successfully connected or not.
        """
        logger.debug(f"Advertising as PiCam named {self._cam_name}")
        try:
            service = nw0.advertise(self._cam_name, ttl_s=timeout)
        except nw0.core.SocketTimedOutError:
            return False
        logger.debug(f"Opening socket on port {self._port}")
        address = nw0.wait_for_message_from(service)
        nw0.send_reply_to(service, self.settings)
        if self._pan_tilting:
            self._driver = PCA9685()
            self._driver.setPWMFreq(50)
        self.write_settings()
        self._server_address = service
        self._client_socket = socket()
        self._client_socket.connect((address, self._port))
        self._connection = self._client_socket.makefile("wb")
        logger.info(f"Successfully connected to {address}:{self._port}")
        self._connected = True
        return True

    def send_image(self) -> bool:
        """
        Send an image from the PiCam.

        :return: A bool on whether we were able to send an image.
        """
        failed = False
        if not self.is_connected:
            raise ValueError("Not connected")
        try:
            img_stream = BytesIO()
            self._cam.capture(img_stream, "jpeg", use_video_port=True)
            img_stream.seek(0)
            img_pil = Image.open(img_stream)
            img_pil = img_pil.rotate(180)
            img_stream.seek(0)
            img_stream.truncate()
            img_pil.save(img_stream, "jpeg")
            self._connection.write(struct.pack("<L", img_stream.tell()))
            self._connection.flush()
            img_stream.seek(0)
            self._connection.write(img_stream.read())
            img_stream.seek(0)
            img_stream.truncate()
            return True
        except Exception:
            failed = True
        finally:
            if failed:
                try:
                    self.disconnect()
                except OSError:
                    pass
                self._connected = False
        return False

    def service_settings(self) -> None:
        """
        Check for requests to change the settings and apply them if needed.

        :return: None.
        """
        result = nw0.wait_for_message_from(self._server_address, wait_for_s=0)
        if result is not None:
            if not self._pan_tilting:
                if self.settings["servos"]["pan"]["value"] != \
                        result["servos"]["pan"]["value"]:
                    logger.error("Pan/tilting disabled!")
                    nw0.send_reply_to(self._server_address,
                                      (False, self.settings))
                    return
                if self.settings["servos"]["tilt"]["value"] != \
                        result["servos"]["tilt"]["value"]:
                    logger.error("Pan/tilting disabled!")
                    nw0.send_reply_to(self._server_address,
                                      (False, self.settings))
                    return
            self.settings = result
            try:
                self.write_settings()
            except Exception:
                logger.exception(f"Error while parsing settings!")
                nw0.send_reply_to(self._server_address, (False, self.settings))
            else:
                logger.info("Successfully set new settings!")
                nw0.send_reply_to(self._server_address, (True, self.settings))

    def write_settings(self) -> None:
        """
        Update the settings in the camera and servos.

        :return: None.
        """
        self._cam.awb_mode = self.settings["awb_mode"]["selected"]
        self._cam.brightness = self.settings["brightness"]["value"]
        self._cam.contrast = self.settings["contrast"]["value"]
        self._cam.image_effect = self.settings["effect"]["selected"]
        self._cam.iso = self.settings["iso"]["selected"]
        self._cam.resolution = self.settings["resolution"]["selected"]
        self._cam.saturation = self.settings["saturation"]["value"]
        if self._pan_tilting:
            self._driver.setRotationAngle(1, self.settings["servos"]["pan"]["value"])
            self._driver.setRotationAngle(0, self.settings["servos"]["tilt"]["value"])

    def disconnect(self) -> None:
        """
        Disconnect.

        :return: None.
        """
        logger.warning("Disconnecting")
        self._connection.close()
        self._client_socket.close()
        self._connected = False
        if self._pan_tilting:
            self._driver.exit_PCA9685()

    @property
    def is_connected(self) -> bool:
        """
        Get whether we are currently connected to a PiCam or not.

        :return: A bool.
        """
        return self._connected
