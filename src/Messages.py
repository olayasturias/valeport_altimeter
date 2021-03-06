class Message(object):
    """
    Enumeration of available messages

    """

    CONFIGURATION_PARAM = 0

    # Instrument settings
    SW_VERSION       = 0x303332 # 032
    UNIT_SERIAL_NUM  = 0x303334 # 034
    PCB_SERIAL_NUM   = 0x313336 # 136
    CALIBRATION_DATE = 0x313338 # 138
    TRANSDUCER_FREQ  = 0x383339 # 839

    # Communication settings
    BAUD_RATE         = 0x303539 # 059
    SET_ADDRESS_485   = 0x303031 # 001
    ADDRESS_485       = 0x303032 # 002
    ADDRESS_MODE_CONF = 0x303035 # 005
    ADDRESS_MODE      = 0x303036 # 006

    # Analogue settings
    SET_VOLTAGE_RANGE       = 0x303934 # 094
    VOLTAGE_RANGE           = 0x303935 # 095
    ANALOG_OUTPUT_TEST      = 0x303936 # 096
    SET_ANALOG_RANGE_LIMIT  = 0x303937 # 097
    ANALOG_RANGE_LIMIT      = 0x303938 # 098

    # Sampling regime
    SINGLE_MEASURE      = 0x53 # hex value of 'S'
    DATA                = '$' #
    MEASURE             = 0x4D # hex value of 'M'
    CONFIGURE           = 0x23 # hex value of #
    READY_2_CONFIGURE   = '>'
    SET_MEASURE_MODE    = 0x303339 # 039
    OPERATING_MODE      = 0x303430 # 040
    RUN                 = 0x303238 # 028

    # Output format
    OUTPUT_FORMAT       = 0x303238 # 089
    SET_OUTPUT_FORMAT   = 0x303832 # 082

    # Range settings
    SET_RANGE_UNITS     = 0x303231 # 021
    RANGE_UNITS         = 0x303232 # 022
    SET_ERROR_MSG       = 0x313138 # 118
    ERROR_MSG           = 0x313139 # 119
    MAX_RANGE           = 0x383234 # 824
    MINIMUM_RANGE       = 0x383431 # 841
    CHANGE_SOUND_SPEED  = 0x383330 # 830
    SOUND_SPEED         = 0x383331 # 831

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
