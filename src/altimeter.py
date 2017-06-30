#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import serial
import bitstring
import binascii
import select
import datetime


class SonarNotFound(Exception):
    """Sonar port could not be found."""
    pass

class PacketIncomplete(Exception):
    """Packet is incomplete."""
    pass

class PacketCorrupted(Exception):
    """Packet is corrupt."""
    pass

class SonarNotConfigured(Exception):
    """Sonar is not configured for scanning."""
    pass

class TimeoutError(Exception):
    """Communication timed out."""
    pass

class Message(object):
    """
    Enumeration of available messages

    """
    # Instrument settings
    SW_VERSION = 32
    UNIT_SERIAL_NUM = 34
    PCB_SERIAL_NUM = 136
    CALIBRATION_DATE = 138
    TRANSDUCER_FREQ = 839

    # Communication settings
    BAUD_RATE = 59
    SET_ADDRESS_485 = 1
    ADDRESS_485 = 2
    ADDRESS_MODE_CONF = 5
    ADDRESS_MODE = 6

    # Analogue settings
    SET_VOLTAGE_RANGE = 94
    VOLTAGE_RANGE = 95
    ANALOG_OUTPUT_TEST = 96
    SET_ANALOG_RANGE_LIMIT = 97
    ANALOG_RANGE_LIMIT = 98

    # Sampling regime
    SINGLE_MEASURE = 'S'
    MEASURE = 'M'
    SET_MEASURE_MODE = 39
    OPERATING_MODE = 40
    RUN = 28

    # Output format
    OUTPUT_FORMAT = 89
    SET_OUTPUT_FORMAT = 82

    # Range settings
    SET_RANGE_UNITS = 21
    RANGE_UNITS = 22
    SET_ERROR_MSG = 118
    ERROR_MSG = 119
    MAX_RANGE = 823
    MINIMUM_RANGE = 841
    CHANGE_SOUND_SPEED = 830
    SOUND_SPEED = 831

    @classmethod
    def to_string(cls,id):
        """
        Get human-readable name corresponding to message id
        :param cls:
        :param id: message ID
        :return:
        """
        for attr, value in cls.__dict__.iteritems():
            if value == id:
                return attr
        else:
            return None

    @classmethod
    def from_string(cls, name):
        """
        Gets message ID corresponding to human-readable name.
        :param name: Human-readable string
        :return:
        """
        if hasattr(cls,name):
            return cls.__getattribute__(name)
        else:
            return None

class Reply(object):
    """
    Parses and verifies reply packages
    """
    def __init__(self, bitstream):
        """

        :param bitstream:
        """
        self.bitstream = bitstream
        self.id = 0
        self.name = "<unknown>"
        self.payload = None

        self.parse()

    def parse(self):
        """
        Parses packet into header, message ID and payload
        :return:
        """
        try:
            # Parse message header
            self.bitstream.bytepos = 0
            rospy.logdebug("parsing message")
            if self.bitstream.endswith("\n"):
                header = self.bitstream.read("uint:8")
            else:
                raise PacketIncomplete("Packet does not end with carriage return")

            if header != 0x23:
                raise PacketCorrupted("Unexpected header: {}".format(header))

            self.bitstream.bytepos = 1
            self.id = self.bitstream.read("uint:8")
            print self.id

            self.bitstream.bytepos = 2
            self.payload = self.bitstream.read("uint:8")

        except ValueError as e:
            raise PacketCorrupted("Unexpected error", e)




class Command(object):
    """
    Sonar commands
    """
    def __init__(self, id, payload = None):
        """
        Construct command object
        :param id:
        :param payload:
        """
        if type(id) == str:
            self.id = bin(int(binascii.hexlify(id),8))
        else:
            self.id = id

        self.payload = payload if payload else bitstring.BitStream()

    def serialize(self):
        """
        Construct string of bytes to send to sonar
        :return:
        """
        values = {
            "id": self.id,
            "payload_length": self.payload.length,
            "payload": self.payload
        }

        serial_format = (
            "0x23, id, 0x3B, bits:payload_length=payload, 0x0D0A"
        )

        message = bitstring.pack(serial_format, **values)

        return message.tobytes()

class Socket(object):
    """
    Sonar connection
    """
    def __init__(self, port,baudrate):
        """

        :param port:
        :param baudrate:
        """
        self.conn = serial.Serial(port=port, baudrate=baudrate)

    def open(self):
        """
        Opens serial connection
        :return:
        """
        self.conn.open()

    def close(self):
        """
        Closes serial connection
        :return:
        """
        self.conn.close()

    def send(self, message, payload = None):
        """

        :param message:
        :param payload:
        :return:
        """
        cmd = Command(message, payload)
        rospy.logdebug("Sending %s: %s", Message.to_string(message), payload)
        self.conn.write(cmd.serialize())

    def get_reply(self):
        """
        Waits for and returns reply
        :return:
        """
        try:
            # Wait for the # character
            # Don't put anything in this while, because if losses packets if you do so
            while not self.conn.read() == "#":
                pass

            rospy.logdebug("Received valid packet (starts with '#') ")

            # Read one line a t a time until packet complete and parsed
            packet = bitstring.BitStream("0x23")

            while True:
                current_line = self.conn.readline()
                for char in current_line:
                    packet.append("0x{:02X}".format(ord(char)))

                # Try to parse
                try:
                    reply = Reply(packet)
                    break
                except PacketIncomplete:
                    # Keep looking
                    continue

            rospy.logdebug("Received %s: %s", reply.name, reply.payload)
            return reply

        except select.error as (code,msg):
            if code == errno.EINTR:
                raise KeyboardInterrupt()
            raise




class VA500(object):
    """
    *VA500* class for sonar altimeter
    """
    def __init__(self, port="/dev/serial", baudrate = 115200):
        """

        :param port:
        :param baudrate: Baud rate, 115200 by default (can be 9600-115200)
        """
        self.port = port
        self.baudrate = baudrate

        self.conn = None
        self.initialized = False

    def __enter__(self):
        """
        Initializes for first use
        """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Cleans up
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        self.close()
        rospy.loginfo("Closed sonar altimeter on %s", self.port)

    def open(self):
        """
        Initializes sonar connection
        :return:
        """
        if not self.conn:
            try:
                self.conn = Socket(self.port, self.baudrate)
            except OSError as e:
                raise SonarNotFound(self.port,e)

        rospy.loginfo("Initializing sonar altimeter on %s", self.port)
        self.initialized = True

        self.conn.send(Message.TRANSDUCER_FREQ)
        self.conn.get_reply()


    def close(self):
        self.conn.close()

    def scan(self):
        """
        Sends command to scan
        :return:
        """
        # send here something to verify sonar is connected?
        if not self.initialized:
            raise SonarNotConfigured(self.initialized)
        # Timeout count
        timeout_count = 0
        MAX_TIMEOUT_COUNT = 5

        # Scan until stopped
        self.preempted = False
        while not self.preempted
            # Preempt on ROS shutdown
            if rospy.is_shutdown():
                self.preempt()
                return
            # Ask sonar to send a single measurement
            self.conn.send(Message.SINGLE_MEASURE)

            # Get the scan data
            try:
                data = self.get(None,wait = 1).payload
                timeout_count = 0
            except TimeoutError:
                timeout_count += 1
                rospy.logdebug("Timeout count: %d", timeout_count)
                if timeout_count >= MAX_TIMEOUT_COUNT:
                    # Try to resend paramenters
                    self.conn.send(Message.SINGLE_MEASURE)
                    timeout_count = 0
                # Try again
                continue
        # Publish extracted data in personalised msg



    def get(self, message = None, wait = 2):
        """
        Sends command and returns reply
        :param message: Message to expect
        :param wait: Seconds to wait until received
        :return:
        """
        # Verify if sonar is initialized
        if not self.initialized:
            raise SonarNotConfigured

        expected_name = Message.to_string(message)
        if message:
            rospy.logdebug("Waiting for % message", expected_name)

        # Determine end time
        end = datetime.datetime.now() + datetime.timedelta(seconds=wait)

        # Wait until received if a specific message ID is requested, otherwise wait forever
        while message is None or datetime.datetime.now() < end:
            try:
                reply = self.conn.get_reply()

                if message is None:
                    return reply
                # Verify reply ID if requested
                if reply.id == message:
                    rospy.logdebug("Found %s message", expected_name)
                    return reply
                else
                    rospy.logwarn("Received unexpected %s message", reply.name)
            except PacketCorrupted, serial.SerialException:
                # Keep trying
                continue
        # Timeout
        rospy.logerr("Timed out before receiving message: %s", expected_name)
        raise TimeoutError()

    def preempt(self):
        """
        Preempts a scan in progress
        :return:
        """
        rospy.logwarn("Preempting scan...")
        self.preempted = True


if __name__ == "__main__":
    # Initialize node
    rospy.init_node('valeport_altimeter', log_level=rospy.DEBUG)

    port = '/dev/ttyUSB0'
    baudrate = 115200

    with VA500(port,baudrate) as va500_altimeter:
        pass

