import getopt
import os
import logging
import sys
import socket
import threading
import glob
import threading
import serial
import logging
import codecs
import binascii
import struct
from twisted.internet import reactor, protocol, endpoints
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor, protocol, endpoints
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort


logger = logging.getLogger("Ensemble File Report")
logger.setLevel(logging.DEBUG)
FORMAT = '[%(asctime)-15s][%(levelname)s][%(funcName)s] %(message)s'
logging.basicConfig(format=FORMAT)

class RtiLogger:
    """
    This is used to initialize the Logging.  This just sets the logging options.
    If you want to also log to a file, then give the file path.
    To Log:

    import logging
    logging.debug("DEBUG MESSAGE")
    """

    # Used to call a global logger
    # logger = logging.getLogger(RtiLogger.LOGGER_NAME)
    # logger.debug("debug message")
    LOGGER_NAME = 'root'

    @staticmethod
    def setup_custom_logger(name='root',
                            log_level=logging.DEBUG,
                            log_format='%(asctime)s - %(levelname)s - %(module)s - (%(threadName)-10s) - %(message)s',
                            file_path=None):

        # If a file path is given, then also log to a file
        if file_path:
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)

        formatter = logging.Formatter(fmt=log_format)

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        logger.addHandler(handler)
        return logger

class SerialDevice(basic.LineReceiver):
    """
    Serial device that will send data to
    all the TCP clients connected.
    Custom serial protocol for the serial port.
    """
    def __init__(self, factory, tcp_server):
        self.factory = factory
        self.tcp_server = tcp_server

    def connectionMade(self):
        """
        Connect the serial port
        """
        logger.debug('Serial Connection made!')

    def connectionLost(self, reason):
        """
        Disconnect the serial port
        """
        #self.factory.clients.remove(self)
        logger.debug('Serial Connection lost ' +  str(reason))
        self.tcp_server.reconnect()

    def dataReceived(self, data):
        """Send data to all the clients
        connected on the TCP port
        """
        #print("Response: {0}", format(data))
        for c in self.tcp_server.factory.clients:
            c.transport.write(data)
            #c.sendLine(data)

    def lineReceived(self, line):
        logger.debug('Serial line received: ', line)

    def rawDataReceived(self, data):
        logger.debug('Serial Raw Data received: ', data)


class SerialTcpProtocol(basic.LineReceiver):
    """
    Create TCP Connections for user that
    want to get serial data
    """

    def __init__(self, factory, comm_port, baud):
        self.factory = factory
        self.comm_port = comm_port
        self.baud = baud

        if self.factory.serial_port is None:
            # Create a Serial Port device to read in serial data
            self.factory.serial_port = SerialPort(SerialDevice(self, self), comm_port, reactor, baudrate=baud)
            logger.debug('Serial Port started')

    def reconnect(self):
        """
        Reconnect the serial connection with the previous serial settings.
        :return:
        """
        self.resetSerialConnection(self.comm_port, self.baud)
        logger.info("Reconnect serial port: " + self.comm_port + " Baud: " + self.baud)

    def resetSerialConnection(self, comm_port, baud):
        """
        Reset the Serial Port device to read in serial data
        """
        self.comm_port = comm_port.strip()
        self.baud = baud
        logger.debug("comm_port: " + self.comm_port)
        logger.debug("Baud: " + str(self.baud))

        logger.debug("Disconnect serial port")
        self.factory.serial_port.loseConnection()

        self.factory.serial_port = SerialPort(SerialDevice(self, self), self.comm_port, reactor, baudrate=self.baud)
        logger.debug('Serial Port Restarted')

    def connectionMade(self):
        """
        Add TCP connections
        """
        self.factory.clients.add(self)
        logger.debug('TCP Connection made')

    def connectionLost(self, reason):
        """
        Disconnect TCP Connections
        """
        self.factory.clients.remove(self)
        logger.debug('TCP Connection lost')

    def dataReceived(self, data):
        """
        Receive data from the TCP port and send the data to the serial port
        """
        # Parse command
        self.parse_cmds(data)

    def lineReceived(self, line):
        logger.debug('TCP line received: ', line)
        #for c in self.factory.clients:
            #source = u"<{}> ".format(self.transport.getHost()).encode("ascii")
            #c.sendLine(source + line)
            #print('line received: ', line)

    def rawDataReceived(self, data):
        logger.debug('TCP Raw data received: ', data)

    def CMD_reconnect(self, cmd):
        """
        Decode the RECONNECT command to configure a new serial port.
        RECONNECT, COM12, 115200
        """
        params = cmd.split(',')
        if len(params) < 3:
            logger.error('Missing parameters to command: ' + cmd)
            return

        # Comm Port
        comm_port = params[1].strip()
        logger.debug("COMM Port: " + comm_port)

        try:
            baud = int(params[2].strip())
            logger.debug("Baud Rate: " + str(baud))
        except Exception as err:
            logger.error('Baud rate must be an integer', err)
            return

        # Reset the serial port
        self.resetSerialConnection(comm_port, baud)
        logger.debug("Reconnect Serial to: " + comm_port + " baud: " + str(baud))

    def CMD_change_baud(self, cmd):
        """
        Decode the BAUD command to configure a new serial port.
        This will reuse the last serial port comm port used.
        BAUD, 115200
        """
        params = cmd.split(',')
        if len(params) < 2:
            logger.error('Missing parameters to command: ' + cmd)
            return

        try:
            baud = int(params[1].strip())
            logger.debug("Baud Rate: " + str(baud))
        except Exception as err:
            logger.error('Baud rate must be an integer', err)
            return

        # Reset the serial port
        self.resetSerialConnection(self.comm_port, baud)
        logger.debug("Change Serial baud to: " + self.comm_port + " baud: " + str(baud))

    def parse_cmds(self, data):
        """
        Parse the commands given by the user.
        """
        logger.debug("Data: " + str(data))
        try:
            # Decode the byte array to a string
            cmd = data.decode('utf-16').strip()

            # Split the commands
            cmd_split = cmd.split(',')
            logger.debug("Command: " + cmd)

            if len(cmd_split) > 0:
                # Make command upper case so do not have to try every combination
                cur_cmd = cmd_split[0].strip().upper()

                if 'BREAK' in cur_cmd:
                    self.factory.serial_port.sendBreak()
                    logger.debug('Hardware BREAK')
                elif 'RECONNECT' in cur_cmd:
                    logger.debug("Attempt to reconnect...")
                    self.CMD_reconnect(cmd)
                elif 'BAUD' in cur_cmd:
                    logger.debug("Attempt to change baud...")
                    self.CMD_change_baud(cmd)
                    logger.debug('Baud Changed')
                else:
                    self.factory.serial_port.write((cmd + "\r").encode())
                    logger.debug("Data: " + str(data))
                    logger.debug("Command: " + cmd)
        except AttributeError as err:
            logger.error("Serial Port error: ", err)
        except Exception as err:
            logger.error("Serial Port Error: ", err)
        #except serial.portNotOpenError as err:
        #    print("Serial Port is not open. ", err)
        #except:
        #    logger.error('Error writing data to serial port')

        source = str(self.transport.getPeer())
        logger.debug(source + " - " + 'TCP data received: ' + cmd)


class AdcpFactory(protocol.Factory):
    """
    Create a serial connection and allow
    TCP clients to view the data
    """
    def __init__(self, comm_port, baud):
        self.clients = set()
        self.serial_port = None
        self.serial_comm_port = comm_port
        self.serial_baud = baud

    def buildProtocol(self, addr):
        return SerialTcpProtocol(self, self.serial_comm_port, self.serial_baud)


class AdcpSerialPortServer:
    """
    Create a serial connection and allow TCP
    clients to view the data
    """
    def __init__(self, port, comm_port, baud):
        self.port = "tcp:" + port       # TCP Port
        self.comm_port = comm_port      # Serial Port
        self.baud = baud                # Baud Rate
        self.thread = None

        logger.info("Start TCP server at: " + str(port))

        # Set the TCP port to output ADCP data
        endpoints.serverFromString(reactor, self.port).listen(AdcpFactory(self.comm_port, self.baud))
        logger.info("Serial port connected on " + str(self.comm_port) + " baud: " + str(baud))
        logger.info("TCP Port open on " + str(self.port))

        # Run the reactor in a thread
        if not reactor.running:
            self.thread = threading.Thread(name='AdcpSerialPort', target=reactor.run, args=(False,)).start()

    def close(self):
        """
        Close the thread to the server
        """
        reactor.stop()
        logger.debug("Reactor Stopped")

        if self.thread is not None:
            self.thread.join()
        logger.debug("ADCP Serial Port Thread stopped")

        #for t in threading.enumerate():
        #    if t.getName() == 'AdcpSerialPort':
        #        t.join()
        #        print("Stop the ADP serial port thread")

    @staticmethod
    def list_serial_ports():
        """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
        """

        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/rs485"
            ports = glob.glob('/dev/rs485')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/rs485')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
                print(port)
            except OSError as err:
                logger.error(err)
                pass
            except serial.SerialException as err:
                logger.error(err)
                pass

        return result

# Set the PORT to output ADCP data
#endpoints.serverFromString(reactor, "tcp:55056").listen(AdcpFactory('/dev/cu.usbserial-FTYNODPO', 115200))
#reactor.run()


class SerialDataRecorder:
    """
    Record the serial data.  This will work as a data logger.
    It will record the serial data and write it to the file path given.
    If no file path is given it will write it in the same directory as
    the application is run.
    """

    # Max file size.  16mbs
    MAX_FILE_SIZE = 1048576 * 16

    # Recorder File name
    RECORDER_FILE_NAME = "Adcp"

    def __init__(self, verbose=False):
        self.serial_server = None
        self.serial_server_thread = None
        self.comm_port = ""
        self.baud = 0
        self.tcp_port = 0
        self.verbose = verbose
        self.folder_path = ''

        self.raw_serial_socket = None
        self.isAlive = True
        self.file = None
        self.file_size = 0
        self.file_name = self.RECORDER_FILE_NAME

    def connect(self, comm_port, baud, folder_path, file_name, tcp_port=55056):
        """
        Connect to the serial port server to receive data.
        :param comm_port: Comm port to connect to.
        :param baud: Baud Rate.
        :param folder_path: Folder path to store the recorded data.
        :param file_name: File name used to create a new file.
        :param tcp_port: TCP Port to receive the data.
        """
        self.comm_port = comm_port
        self.baud = baud
        self.tcp_port = tcp_port
        self.folder_path = folder_path
        self.file_name = file_name
        self.serial_server = AdcpSerialPortServer(tcp_port,
                                                  comm_port,
                                                  baud)

        # Start a tcp connection to monitor incoming data and record
        self.serial_server_thread = threading.Thread(name='AdcpWriter',
                                                     target=self.create_raw_serial_socket(self.tcp_port))
        self.serial_server_thread.start()

    def create_raw_serial_socket(self, port):
        """
        Connect to the ADCP serial server.  This TCP server outputs data from
        the serial port.  Start reading the data.
        """
        try:
            # Create a file
            self.create_file_writer()

            # Create socket
            self.raw_serial_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.raw_serial_socket.connect(('localhost', int(port)))
            self.raw_serial_socket.settimeout(1)    # Set timeout to stop thread if terminated
        except ConnectionRefusedError as err:
            logger.error("Serial Send Socket: ", err)
        except Exception as err:
            logger.error('Serial Send Socket: ", Error Opening socket', err)

        # Start to read the raw data
        self.read_tcp_socket()

    def read_tcp_socket(self):
        """
        Read the data from the TCP port.  This is the raw data from the serial port.
        Then write this data to the file.
        """
        while self.isAlive:
            try:
                # Read data from socket
                data = self.raw_serial_socket.recv(4096)

                # If data exist process
                if len(data) > 0:
                    # Write the data to the file
                    self.file.write(data)

                    # Keep track of the file size
                    self.file_size += len(data)

                    # Limit the output prompt
                    #if self.file_size % 5 == 0:
                    #    print('.', end="", flush=True)

                    # Check the file size to see if a new file needs to be created
                    if self.file_size > self.MAX_FILE_SIZE:
                        self.close_file_write()                 # Close this file
                        self.create_file_writer()               # Open a new file

            except socket.timeout:
                # Just a socket timeout, continue on
                pass
            except Exception as e:
                logger.error("Exception in reading data.", e)
                self.stop_adcp_server()

        print("Read Thread turned off")

    def create_file_writer(self):
        """
        Create a file writer.  This will open the file and have it ready
        to write data to the file.
        """
        file_path = self.get_new_file()
        logger.debug("Open File name: " + file_path)

        self.file_size = 0
        self.file = open(file_path, 'wb')

    def close_file_write(self):
        """
        Close the file.
        """
        logger.debug("Close the file")
        self.file.close()

    def get_new_file(self):
        """
        Create a new file path.  If the file exist,
        update the index until a new unique name is created.
        :return: New File name.
        """
        index = 0
        file_name = self.file_name + str(index)

        if not os.path.isdir(self.folder_path):
            os.makedirs(self.folder_path)

        # Create a new file name
        file_path = os.path.join(self.folder_path, file_name + ".ens")

        # Continue to create a file until a new file name is found
        while os.path.exists(file_path):
            index += 1
            file_name = self.file_name + str(index)
            file_path = os.path.join(self.folder_path, file_name + ".ens")

        return file_path

    def stop_adcp_server(self):
        """
        Stop the ADCP Serial TCP server
        """
        # Stop the thread loop
        self.isAlive = False

        if self.serial_server is not None:
            self.serial_server.close()
            logger.debug("serial server stopped")
        else:
            logger.debug('No serial connection')

        # Close the socket
        self.raw_serial_socket.close()

        # Stop the server thread
        if self.serial_server_thread is not None:
            self.serial_server_thread.join()

        # Close the open file
        self.close_file_write()

        logger.debug("Stop the Recorder")


def main(argv):
    comm_port = '/dev/rs485'
    baud = '115200'
    tcp_port = '55056'
    folder_path = '/mnt/usb/recorder'
    verbose = False
    file_name = "Adcp"
    try:
        opts, args = getopt.getopt(argv, "hlvc:b:f:p:n:", ["comm=", "baud=", "folder=", "name=", "tcp=", "verbose"])
    except getopt.GetoptError:
        print('SerialDataRecorder.py -c <comm> -b <baud> -f <folder> -p <tcp> -n <file_name> -v')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('usage: SerialDataRecorder.py ')
            print('-c <comm>\t : Serial Comm Port.  Use -l to list all the ports.')
            print('-b <baud>\t : Serial Baud Rate. Default 115200.')
            print('-p <tcp>\t : TCP Port to output the serial data.  Default 55056.  Change if used already.')
            print('-f <folder>\t : Folder path to store the serial data.  Default is same path as application.')
            print('-n <file_name>\t : File name for the files.  Default is "Adcp.')
            print('-v\t : Verbose output.')
            print('Utilities:')
            print('-l\t : Print all available Serial Ports')
            sys.exit()
        elif opt == '-l':
            AdcpSerialPortServer.list_serial_ports()
            sys.exit()
        elif opt in ('-c', "--comm"):
            comm_port = arg
        elif opt in ("-b", "--baud"):
            baud = arg
        elif opt in ("-f", "--folder"):
            folder_path = arg
        elif opt in ("-p", "--tcp"):
            tcp_port = arg
        elif opt in ("-n", "--name"):
            file_name = arg
        elif opt in ("-v", "--verbose"):
            verbose = True
            print("Verbose ON")
    print('Comm Port: ', comm_port)
    print('Baud Rate: ', baud)
    print('TCP Port: ', tcp_port)
    print('Folder Path: ', folder_path)
    print('File Name: ', file_name)
    print("Available Serial Ports:")
    serial_list = AdcpSerialPortServer.list_serial_ports()

    # Verify a good serial port was given
    if comm_port in serial_list:
        # Run serial port
        sdr = SerialDataRecorder(verbose).connect(comm_port, baud, folder_path, file_name, tcp_port)
        sdr.stop_adcp_server()
    else:
        print("----------------------------------------------------------------")
        print("BAD SERIAL PORT GIVEN")
        print("Please use -c to give a good serial port.")
        print("-l will give you a list of all available serial ports.")

if __name__ == "__main__":
    main(sys.argv[1:])

