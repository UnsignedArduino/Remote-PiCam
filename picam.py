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
        self._connection = None
        self._connected = False

    def connect(self) -> bool:
        """
        Actually connect to the server.

        :return: A bool on whether we successfully connected or not.
        """
        logger.debug(f"Advertising as PiCam named {self._cam_name}")
        service = nw0.advertise(self._cam_name)
        self._client_socket = socket()
        logger.debug(f"Opening socket on port {self._port}")
        address = nw0.wait_for_message_from(service, autoreply=True)
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
