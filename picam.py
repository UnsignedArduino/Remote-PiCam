import logging
import struct
from io import BytesIO
from socket import socket
from typing import Union

import networkzero as nw0
from PIL import Image

from create_logger import create_logger
import picamera

logger = create_logger(name=__name__, level=logging.DEBUG)


class NetworkPiCam:
    """
    A class to manage connecting and sending images as a PiCam.
    """

    def __init__(self, cam: picamera, cam_name: str, port: int):
        """
        Initiate the PiCam. This does not actually connect to the PiCam until
        you call connect().

        :param cam: The PiCamera object.
        :param cam_name: The name of the PiCamera. This is used by the other
         end to discover the camera.
        :param port: The port to connect to
        """
        self._cam = cam
        self._cam_name = cam_name
        self._port = port
        self._client_socket = None
        self._server_address = None
        self._connection = None
        self._connected = False
        self.settings = {
            "resolution": (720, 480)
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
        address = nw0.wait_for_message_from(service, autoreply=True)
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
            self._cam.capture(img_stream, "jpeg")
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
                self._connection.close()
                self._client_socket.close()
                self._connected = False
        return False

    def service_settings(self) -> None:
        """
        Check for requests to change the settings and apply them if needed.

        :return: None.
        """
        result = nw0.wait_for_message_from(self._server_address, wait_for_s=0)
        if result is not None:
            self.settings = result
            try:
                self._cam.resolution = self.settings["resolution"]
            except Exception:
                logger.exception(f"Error while parsing settings!")
                nw0.send_reply_to(self._server_address, (False, self.settings))
            else:
                logger.info("Successfully set new settings!")
                nw0.send_reply_to(self._server_address, (True, self.settings))

    def disconnect(self) -> None:
        """
        Disconnect.

        :return: None.
        """
        logger.warning("Disconnecting")
        self._connection.close()
        self._client_socket.close()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """
        Get whether we are currently connected to a PiCam or not.

        :return: A bool.
        """
        return self._connected
