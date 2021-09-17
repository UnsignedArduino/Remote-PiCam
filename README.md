# Remote-PiCam
View and control a Raspberry Pi Camera mounted on a Waveshare pan/tilt HAT!

## Installation

1. Set up a Raspberry Pi. The GUI is not needed on the Pi, so you can use SSH. 
2. Obtain and connect a 
   [Raspberry Pi Camera](https://www.raspberrypi.org/products/camera-module-v2/).
3. Optional: Obtain, assemble, and connect a 
   [Waveshare Pan-Tilt HAT](https://www.waveshare.com/pan-tilt-hat.htm).
4. `git clone` this repo and `cd` into it.  
5. Optional: Create a virtual environment with `python3 -m venv .venv` and then
   activate the virtual environment with`source .venv/bin/activate`. 
6. Install dependencies with `pip3 install -r requirements.txt`. (You can find
   the list of dependencies in the 
   [`requirements.txt`](https://github.com/UnsignedArduino/Remote-PiCam/blob/main/requirements.txt) 
   file. )

## Usage
To run, first start trying to connect using the 
[Remote PiCam Viewer](https://github.com/UnsignedArduino/Remote-PiCam-Viewer).
Then, run 
[`main.py`](https://github.com/UnsignedArduino/Remote-PiCam/blob/main/main.py). 
When you disconnect from the PiCam, the script will stop, so you will have to
re-run the script if you want to reconnect. 

## Configuration
When you first run the script, a `settings.json` file should generate:
```json
{
    "camera": {
        "name": "picam",
        "port": 7896
    },
    "pan_tilt": {
        "enable": true
    }
}
```
`camera.name` and `camera.port` should match in the PiCam Viewer settings, 
otherwise the software won't discover it (`name` is not correct) or it will
stay connecting forever and get stuck. (`port` is not correct)

`pan_tilt.enable` should be `true` if you have a Waveshare Pan/Tilt HAT 
connected, otherwise `false`.
