#
# Driver for sx127x chip.
#
# Designed to be inherited by worker class to perform the actual I/O
#
import gc
import _thread
from thread import recursive_lock

try:
    _UNUSED_=const(1)
except:
    # In case this is needed
    const = lambda x: x


# Register definitions
_SX127x_REG_FIFO                 = const(0x00)     # Read/write fifo
_SX127x_REG_OP_MODE              = const(0x01)     # Operation mode
_SX127x_MODE_LONG_RANGE             = const(0x80)
_SX127x_MODE_MODULATION_FSK         = const(0x00)  # FSK
_SX127x_MODE_MODULATION_OOK         = const(0x40)  # OOK
_SX127x_MODE_LOW_FREQUENCY          = const(0x08)  # Low frequency mode on
_SX127x_MODE_SLEEP                  = const(0x00)
_SX127x_MODE_STANDBY                = const(0x01)
_SX127x_MODE_FS_TX                  = const(0x02)
_SX127x_MODE_TX                     = const(0x03)
_SX127x_MODE_FS_RX                  = const(0x04)
_SX127x_MODE_RX_CONTINUOUS          = const(0x05)
_SX127x_MODE_RX_SINGLE              = const(0x06)
# 0x02 through 0x05 not used
_SX127x_REG_FREQ_MSB             = const(0x06)     # Carrier MSB
_SX127x_REG_FREQ_MID             = const(0x07)     # Carrier Middle
_SX127x_REG_FREQ_LSB             = const(0x08)     # Carrier LSB
_SX127x_REG_PA_CONFIG            = const(0x09)
_SX127x_PA_BOOST                    = const(0x80)
_SX127x_REG_PA_RAMP              = const(0x0A)     # Controls ramp time / low phase noise PLL
_SX127x_REG_OCP                  = const(0x0B)     # Over-current protection control
_SX127x_REG_LNA                  = const(0x0C)     # LNA settings
_SX127x_REG_FIFO_PTR             = const(0x0D)     # FIFO SPI Pointer
_SX127x_REG_TX_FIFO_BASE         = const(0x0E)     # Start TX data
_SX127x_REG_RX_FIFO_BASE         = const(0x0F)     # Start RX data
_SX127x_REG_RX_FIFO_CURRENT      = const(0x10)     # Start addr of last packet received
_SX127x_REG_IRQ_FLAGS_MASK       = const(0x11)     # Optional IRQ flag mask
_SX127x_REG_IRQ_FLAGS            = const(0x12)     # IRQ flags
_SX127x_REG_CAD_DETECTED            = const(0x01)
_SX127x_REG_FHSS_CHANGE_CHANNEL     = const(0x02)
_SX127x_IRQ_CAD_COMPLETE            = const(0x04)
_SX127x_IRQ_TX_DONE                 = const(0x08)
_SX127x_IRQ_VALID_HEADER            = const(0x10)
_SX127x_IRQ_PAYLOAD_CRC_ERROR       = const(0x20)
_SX127x_IRQ_RX_DONE                 = const(0x40)
_SX127x_IRQ_RX_TIMEOUT              = const(0x80)
_SX127x_REG_RX_NUM_BYTES         = const(0x13)     # Number of received bytes
_SX127x_REG_RX_HEADER_CNT_MSB    = const(0x14)     # Number of valid headers MSB
_SX127x_REG_RX_HEADER_CNT_LSB    = const(0x15)     # Number of valid headers LSB
_SX127x_REG_RX_PACKET_CNT_MSB    = const(0x16)     # Number of packets MSB
_SX127x_REG_RX_PACKET_CNT_LSB    = const(0x17)     # Number of packets LSB
_SX127x_REG_MODEM_STATUS         = const(0x18)     # Live modem status
_SX127x_REG_PACKET_SNR           = const(0x19)     # SNR estimate of last packet
_SX127x_REG_PACKET_RSSI          = const(0x1A)     # Last packet RSSI value
_SX127x_REG_RSSI_VALUE           = const(0x1B)     # Current SNR value
_SX127x_REG_HOP_CHANNEL          = const(0x1C)     # FHSS Start channel
_SX127x_REG_MODEM_CONFIG_1       = const(0x1D)     # Modem PHY config 1
_SX127x_REG_MODEM_CONFIG_2       = const(0x1E)     # Modem PHY config 2
_SX127x_REG_SYMBOL_TIMEOUT       = const(0x1F)     # Receiver timeout value
_SX127x_REG_PREAMBLE_MSB         = const(0x20)     # Size of preamble MSB
_SX127x_REG_PREAMBLE_LSB         = const(0x21)     # Size of preamble LSB
_SX127x_REG_PAYLOAD_LENGTH       = const(0x22)     # Payload length
_SX127x_REG_MAX_PAYLOAD_LENGTH   = const(0x23)     # Max payload length
_SX127x_REG_HOP_PERIOD           = const(0x24)     # FHSS Hop period
_SX127x_REG_RX_FIFO_BYTE         = const(0x25)     # Address of last byte written to FIFO
_SX127x_REG_MODEM_CONFIG_3       = const(0x26)     # Modem PHY config 3
# 0x27 reserved
_SX127x_REG_FEI_MSB              = const(0x28)     # Estimated frequency error MSB
_SX127x_REG_FEI_MID              = const(0x29)     # Estimated frequency error MID
_SX127x_REG_FEI_LSB              = const(0x2A)     # Estimated frequency error LSB
# 0x2B reserved
_SX127x_REG_RSSI_WIDEBAND        = const(0x2c)     # Wideband RSSI measurement
# 0x2D to 02x30 reserved
_SX127x_REG_DETECTION_OPTIMIZE   = const(0x31)     # LoRa detection optimize for SF6
# 0x32 reserved
_SX127x_REG_INVERT_IQ            = const(0x33)     # Invert I and Q signals
# 0x34 through 0x36 reserved
_SX127x_REG_DETECTION_THRESHOLD  = const(0x37)     # LoRa detection threshold for SF6
# 0x38 reserved
_SX127x_REG_SYNC_WORD            = const(0x39)     # Sync word
# 0x3A through 0x3F reserved
_SX127x_REG_DIO_MAPPING_1        = const(0x40)     # Mapping of DIO 0, 1, 2 and 3
_SX127x_REG_DIO_MAPPING_2        = const(0x41)     # Mapping of DIO 4, 5 and ClkOut
_SX127x_REG_VERSION              = const(0x42)     # Returns SEMTECH IC Version
# 0x43 through 0x4A reserved
_SX127x_REG_TCXO                 = const(0x4B)     # TCXO or Crystal input setting
# 0x4C reserved
_SX127x_REG_PA_DAC               = const(0x4D)     # Higher power settings of PA
# 0x4E through 0x60 not used
_SX127x_REG_AGC_REG              = const(0x61)     # Adjustments ...
_SX127x_REG_AGC_THRESHOLD_1      = const(0x62)     # ... of ...
_SX127x_REG_AGC_THRESHOLD_2      = const(0x63)     # ... AGC ...
_SX127x_REG_AGC_THRESHOLD_3      = const(0x64)     # ... Thresholds
# 0x65 through 0x6F not used
_SX127x_REG_PLL                  = const(0x70)     # Constrols PLL bandwidth
# 0x71 through 0x7F test mode - not used

# Other consts
_SX127x_MAX_PACKET_LENGTH        = const(255)

_TX_FIFO_BASE              = const(0x00)
_RX_FIFO_BASE              = const(0x00)

_FREQUENCIES = {
        196: (42, 64, 0),
        433: (108, 64, 0),
        434: (108, 128, 0),
        866: (216, 128, 0),
        868: (217, 0, 0),
        915: (228, 192, 0),
}

# SX127x driver class
# Must be inherited by an object that contains the following members:
# Required:
#    read_register(<register>)                         Return register value
#
#    write_register(<register>, <value>                Write register value
#
#    attach_interrupt(<callback>)                      Enable interrupt, callback supplied (None causes disable)
#         Call attach_interrupt with None callback to disable
#
#    onReceive(packet, crc_ok, rssi)                   Callback to receive a packet
#
#    onTransmit()                                      Callback when packet has been transmitted
#                                                      Returns next packet if more to send
#
#    reset()                                           Reset device
#
#  Optional:
#    write_buffer(<register>, <bytearray of values>, size)   Optional: write a packet
#    read_buffer(<register>, <length>                  Optional: read a packet
#

class SX127x_driver:

    def __init__(self,
                 frequency = 915,
                 tx_power = 2,
                 bandwidth = 125e3,
                 spreading_factor = 8,
                 coding_rate = 5,
                 preamble_length = 8,
                 implicit_header = False,
                 sync_word = 0x12,
                 enable_crc = False):
        self._frequency = frequency
        self._tx_power = tx_power
        self._bandwidth = bandwidth
        self._spreading_factor = spreading_factor
        self._coding_rate = coding_rate
        self._preamble_length = preamble_length
        self._implicit_header = implicit_header
        self._sync_word = sync_word
        self._enable_crc = enable_crc

        self._current_implicit_header = None

        self._lock = recursive_lock()


    def init(self, wanted_version=0x12, start=True):
        # help(self)

        self.reset()

        # Read version
        version = None
        max_tries = 5
        while version != wanted_version and max_tries != 0:
            version = self.read_register(_SX127x_REG_VERSION)
            max_tries = max_tries - 1

        if version != wanted_version:
            raise Exception("Wrong version detected: %02x wanted %02x" % (version, wanted_version))

        # Put receiver in sleep
        self._set_sleep_mode()

        # Configure the unit
        self.set_frequency(self._frequency)
        self.set_bandwidth(self._bandwidth)

        # LNA Boost
        self.write_register(_SX127x_REG_LNA, self.read_register(_SX127x_REG_LNA) | 0x03)  # MANIFEST CONST?

        # auto AGC enable
        self.write_register(_SX127x_REG_MODEM_CONFIG_3, 0x04)  # MANIFEST??

        # Set parameters
        self.set_tx_power(self._tx_power)
        self.set_implicit_header(self._implicit_header)
        self.set_spreading_factor(self._spreading_factor)
        self.set_coding_rate(self._coding_rate)
        self.set_preamble_length(self._preamble_length)
        self.set_sync_word(self._sync_word)
        self.set_enable_crc(self._enable_crc)

        # Set 'low data rate' flag if long symbol time
        if 1000 / (self._bandwidth / 2**self._spreading_factor) > 16:
            self.write_register(_SX127x_REG_MODEM_CONFIG_3, self.read_register(_SX127x_REG_MODEM_CONFIG_3) | 0x08) # MANIFIEST

        self.write_register(_SX127x_REG_TX_FIFO_BASE, _TX_FIFO_BASE) 
        self.write_register(_SX127x_REG_RX_FIFO_BASE, _RX_FIFO_BASE) 

        # Mask all but Tx and Rx
        self.write_register(_SX127x_REG_IRQ_FLAGS_MASK, 0xFF & ~(_SX127x_IRQ_TX_DONE | _SX127x_IRQ_RX_DONE))
        # Clear all interrupts
        self.write_register(_SX127x_REG_IRQ_FLAGS, 0xFF)

        if start:
            # Place in standby mode
            self._set_receive_mode()
        else:
            self._set_standby_mode()


    # If we cannot do a block write, write byte at a time
    # Can be overwritten by base class to achieve better throughput
    def write_buffer(self, address, buffer):
        # print("write_buffer: '%s'" % buffer.decode())
        for i in range(len(buffer)):
            self.write_register(address, buffer[i])

    # If user does not define a block write, do it the hard way
    def read_buffer(self, address, length):
        buffer = bytearray()
        for l in range(length):
            buffer.append(self.read_register(address))
        self._garbage_collect()
        return buffer

    # Must be overriden by base class
    def write_register(self, reg, value):
        raise Exception("write_register not defined.")

    def read_register(self, reg):
        raise Exception("read_register not defined.")

    def attach_interrupt(self, callback):
        raise Exception("enable_interrupt not defined.")

#    def get_irq_flags(self):
#        flags = self.read_register(_SX127x_REG_IRQ_FLAGS)
#        self.write_register(_SX127x_REG_IRQ_FLAGS, flags)
#        return flags


    def get_packet_rssi(self):
        rssi = self.read_register(_SX127x_REG_PACKET_RSSI) - 157
        if self._frequency < 868E6:
            rssi = rssi + 7
        return rssi

    def get_packet_snr(self):
        return self.read_register(_SX127x_REG_PACKET_SNR) / 4.0

    def _set_standby_mode(self):
        # print("standby mode")
        self.write_register(_SX127x_REG_OP_MODE, _SX127x_MODE_LONG_RANGE | _SX127x_MODE_STANDBY)

    def _set_sleep_mode(self):
        # print("sleep mode")
        self.write_register(_SX127x_REG_OP_MODE, _SX127x_MODE_LONG_RANGE | _SX127x_MODE_SLEEP)

    def _set_receive_mode(self):
        # print("receive mode")
        # self.write_register(_SX127x_REG_OP_MODE, _SX127x_MODE_LONG_RANGE | _SX127x_MODE_RX_SINGLE)
        self.write_register(_SX127x_REG_OP_MODE, _SX127x_MODE_LONG_RANGE | _SX127x_MODE_RX_CONTINUOUS)
        self.attach_interrupt(self._rxhandle_interrupt)
        self.write_register(_SX127x_REG_DIO_MAPPING_1, 0b00000000)

    def _set_transmit_mode(self):
        # print("transmit mode")
        self.write_register(_SX127x_REG_OP_MODE, _SX127x_MODE_LONG_RANGE | _SX127x_MODE_TX)
        self.attach_interrupt(self._txhandle_interrupt)
        self.write_register(_SX127x_REG_DIO_MAPPING_1, 0b01000000)

    def set_tx_power(self, level, mode="RFO"):
        if mode == "PA":
            # PA Boost mode
            self.write_register(_SX127x_REG_PA_CONFIG, PA_BOOST | (min(max(level, 2), 17)) - 2)
        else:
            self.write_register(_SX127x_REG_PA_CONFIG, 0x70 | (min(max(level, 0), 14)))

    def set_frequency(self, frequency):
        if frequency in _FREQUENCIES:
            self.write_register(_SX127x_REG_FREQ_MSB, _FREQUENCIES[frequency][0])
            self.write_register(_SX127x_REG_FREQ_MID, _FREQUENCIES[frequency][1])
            self.write_register(_SX127x_REG_FREQ_LSB, _FREQUENCIES[frequency][2])
        else:
            raise Exception("Invalid frequency: %.1f" % frequency)

    def set_bandwidth(self, bandwidth):
        # Taken from github
        bins = (7.8E3, 10.4E3, 15.6E3, 20.8E3, 31.25E3, 41.7E3, 62.5E3, 125E3, 250E3)

        bw = 9
        for i in range(len(bins)):
            if bandwidth <= bins[i]:
                bw = i
                break

        self.write_register(_SX127x_REG_MODEM_CONFIG_1,
                           ( self.read_register(_SX127x_REG_MODEM_CONFIG_1) & 0x0f) | (bw << 4))

    def set_spreading_factor(self, spreading_factor):
        sf = min(max(spreading_factor, 6), 12)
        self.write_register(_SX127x_REG_DETECTION_OPTIMIZE, 0xc5 if sf == 6 else 0xc3)
        self.write_register(_SX127x_REG_DETECTION_THRESHOLD, 0x0c if sf == 6 else 0x0a)
        self.write_register(_SX127x_REG_MODEM_CONFIG_2,
                            (self.read_register(_SX127x_REG_MODEM_CONFIG_2) & 0x0f) | ((sf << 4) & 0xf0))

    def set_coding_rate(self, rate):
        # Limit it
        rate = min(max(rate, 5), 8)

        self.write_register(_SX127x_REG_MODEM_CONFIG_1, (self.read_register(_SX127x_REG_MODEM_CONFIG_1) & 0xF1) | (rate - 4) << 1)

    def set_preamble_length(self, length):
        self.write_register(_SX127x_REG_PREAMBLE_MSB, (length >> 8))
        self.write_register(_SX127x_REG_PREAMBLE_LSB, length)

    def set_enable_crc(self, enable=True):
        config = self.read_register(_SX127x_REG_MODEM_CONFIG_2)
        if enable:
            config |= 0x04
        else:
            config &= ~0x04
        self.write_register(_SX127x_REG_MODEM_CONFIG_2, config)

    def set_sync_word(self, sync):
        self.write_register(_SX127x_REG_SYNC_WORD, sync)

    def set_implicit_header(self, implicit_header = True):
        if implicit_header != self._current_implicit_header:
            self._current_implicit_header = implicit_header
            config = self.read_register(_SX127x_REG_MODEM_CONFIG_1)
            if implicit_header:
                config |= 0x01
            else:
                config &= ~0x01
            self.write_register(_SX127x_REG_MODEM_CONFIG_1, config)

    # Enable receive mode
    def enable_receive(self, length=0):
        self.set_implicit_header(length != 0)

        if length != 0:
            self.write_register(_SX127x_REG_PAYLOAD_LENGTH, length)

    # Receive interrupt comes here
    def _rxhandle_interrupt(self, event):
        # print("_rxhandle_interrupt fired on %s" % str(event))
        with self._lock:
            # print("Interrupt locked")
            flags = self.read_register(_SX127x_REG_IRQ_FLAGS)

            if flags & _SX127x_IRQ_RX_DONE:
                self.write_register(_SX127x_REG_IRQ_FLAGS, _SX127x_IRQ_RX_DONE)

                self.write_register(_SX127x_REG_FIFO_PTR, self.read_register(_SX127x_REG_RX_FIFO_CURRENT))
                if self._implicit_header:
                    length = self.read_register(_SX127x_REG_PAYLOAD_LENGTH)
                else:
                    length = self.read_register(_SX127x_REG_RX_NUM_BYTES)
                packet = self.read_buffer(_SX127x_REG_FIFO, length)

                crc_ok = (flags & _SX127x_IRQ_PAYLOAD_CRC_ERROR) == 0

                self.onReceive(packet, crc_ok, self.get_packet_rssi())
        self._garbage_collect()

    def _txhandle_interrupt(self, event):
        # print("_txhandle_interrupt fired on %s" % str(event))
        with self._lock:
            flags = self.read_register(_SX127x_REG_IRQ_FLAGS)
            if flags & _SX127x_IRQ_TX_DONE:
                # Say processed
                self.write_register(_SX127x_REG_IRQ_FLAGS, _SX127x_IRQ_TX_DONE)
                packet = self.onTransmit()
                if packet:
                    self.transmit_packet(packet)
                else:
                    self._set_receive_mode()
        self._garbage_collect()

    def _start_packet(self, implicit_header = False):
        self._set_standby_mode()
        self.set_implicit_header(implicit_header)
        self.write_register(_SX127x_REG_FIFO_PTR, _TX_FIFO_BASE)
        self.write_register(_SX127x_REG_PAYLOAD_LENGTH, 0)

    def _write_packet(self, buffer):
        current = self.read_register(_SX127x_REG_PAYLOAD_LENGTH)
        size = min(len(buffer), (_SX127x_MAX_PACKET_LENGTH - _TX_FIFO_BASE - current))

        # print("_write_packet: writing %d: '%s'" % (size, buffer.decode()))

        if size == len(buffer):
            self.write_buffer(_SX127x_REG_FIFO, buffer)
        else:
            self.write_buffer(_SX127x_REG_FIFO, buffer[0:size])
#        for i in range(size):
#            self.write_register(_SX127x_REG_FIFO, buffer[i])

        # print("_write_packet: writing current %d + size %d = %d" % (current, size, current+size))
        self.write_register(_SX127x_REG_PAYLOAD_LENGTH, current + size)

        return size

    def transmit_packet(self, packet, implicit_header = False):
        # print("transmit_packet lock %s" % self._lock.locked())
        with self._lock:
            # print("Starting packet")
            self._start_packet(implicit_header)
            self._write_packet(packet)
            self._set_transmit_mode()
            # print("Unlocked")

    def _garbage_collect(self):
        gc.collect()

    def __exit__(self):
        # Disbable interrupts 
        self.attach_interrupt(None)
        self.write_register(_SX127x_REG_IRQ_FLAGS_MASK, 0xFF)