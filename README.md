# rpi_ADCP_datalogger
Setup required to log data from a Rowetech ADCP to a Raspberry Pi (RPi)
- Instructions include all steps to setup RPi as a local hotspot to control Rpi via tablet.

Note: Credit to @rowetechinc and @ricorx7 for source code (rowetechinc/rpi_datalogger). All code and files are modified for use on a Rowetech SeaWave ADCP and instructions to setup the Raspberry Pi are compiled from various sources. *

Other notes: make sure to update your Rpi to latest version via internet connection, including python. Python dependencies are listed under rpi_ADCP_datalogger/Python_requirements

Instructions for setting up Raspberry Pi as a datalogger are listed under /rpi_ADCP_datalogger/RPI_setup

The goal of the datalogger is to read ADCP binary data from a RS-485 USB adapter. This guide assumes the user knows basic linux operations, file/folder permissions and editing system files.

General steps

1. Download all files from rpi_ADCP_datalogger to a folder on desktop.

2. Mount USB drive to boot to /mnt/usb (https://www.raspberrypi.org/documentation/configuration/external-storage.md) and set permissions to read-write-execute in the cmd line (VERY IMPORTANT!): sudo chmod a+rwx /mnt/usb 

3. Create directories for /home/pi/rti, change Raspberry Pi permissions to read and write for the following folders, and apply permissions also to /lib/systemd/system

4. Copy SerialDataRecorder_rs485.py to home/pi/rti or another suitable easy place to access it (desktop)

5. Copy rti_datalogger.service, rti_downloadserver.service to /lib/systemd/system. rti_datalogger.timer is optional and you can modify the time you want to delay the service to begin, but it isn't necessary as long as you run the following in step 5.

6.  sudo systemctl daemon-reload
    sudo systemctl enable rti_downloadserver.service
    
7. In order to maintain a peristent name for the usb to rs485 converter, we need to change the port name to recognize it every time, depending on where it's plugged in. In order to do this, copy the 

7. Setup ADCP using PulseWaves and prepare a start time, unplug RS485 from ADCP into Raspberry Pi

8. 
