# rpi_ADCP_datalogger
Setup required to log data from a Rowetech ADCP to a Raspberry Pi (RPi)
- Instructions include all steps to setup RPi as a local hotspot to control Rpi via tablet.

Note: Credit to @rowetechinc and @ricorx7 for source code (https://github.com/rowetechinc/rpi_datalogger). All code and files are modified for use on a Rowetech SeaWave ADCP and instructions to setup the Raspberry Pi are compiled from various sources. *

Other notes: make sure to update your Rpi to latest version via internet connection, including python. Python dependencies are listed under rpi_ADCP_datalogger/Python_requirements and MUST be installed on Python 3 and the system before continuing.

Instructions for setting up Raspberry Pi as a datalogger are listed under /rpi_ADCP_datalogger/RPI_setup

The goal of the datalogger is to read ADCP binary data from a RS-485 USB adapter. This guide assumes the user knows basic linux operations, file/folder permissions and editing system files.

General steps

1. Download all files from rpi_ADCP_datalogger to a folder on desktop.

2. Mount USB drive to boot to /mnt/usb (https://www.raspberrypi.org/documentation/configuration/external-storage.md) and set permissions to read-write-execute in the cmd line (VERY IMPORTANT!): sudo chmod a+rwx /mnt/usb 

3. Create directories for /home/pi/rti, change Raspberry Pi permissions to read and write for the following folders, and apply permissions also to /lib/systemd/system AND /etc/udev/rules.d/

4. Copy SerialDataRecorder_rs485.py to home/pi/rti or another suitable easy place to access it (desktop)

5. Copy rti_datalogger.service, rti_downloadserver.service to /lib/systemd/system. rti_datalogger.timer is optional and you can modify the time you want to delay the service to begin, but it isn't necessary as long as you run the following in step 6.

6. ~~~~~~
    sudo systemctl daemon-reload
    sudo systemctl enable rti_downloadserver.service
    
7. In order to maintain a peristent name for the usb to rs485 converter, we need to change the port name to recognize it every time,     depending on where it's plugged in. In order to do this, copy the '99-usb-serial.rules' file to the /etc/udev/rules.d/ 

8. Setup ADCP using PulseWaves and prepare a start time, unplug RS485 from ADCP and plug into Raspberry Pi

9. Go to your SerialDataRecorder_rs485.py and Edit IDLE, then run code. You should receive some red output text indicating a successful connection to the RS-485 adapter and a printed output to wherever the python code is running that indicates datalogger is connected. *TO-DO: Automate this step.

10. Once data is coming in, it should be located in the /mnt/usb folder

********************************************
To create a wireless local access point:

Follow instructions here: https://www.raspberrypi.org/documentation/configuration/wireless/access-point-routed.md

Once you have this set up, you can install VNC Viewer and control the Raspberry Pi setup wirelessly (in our case, standing on a boat).

