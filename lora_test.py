#
# LoRa message driver.
#

from time import sleep
from thread import *
from sx127x import *
import _thread
from machine import SPI, Pin


_SX127x_INT   = const(26)   # Interrupt pin
_SX127x_SCK   = const(5)
_SX127x_MOSI  = const(27)
_SX127x_MISO  = const(19)
_SX127x_SS    = const(18)
_SX127x_RESET = const(14)
_SX127x_WANTED_VERSION = const(0x12)

class LoRaHandler(SX127x_driver, thread):

    def __init__(self):
        SX127x_driver.__init__(self, bandwidth=50e3, spreading_factor=10)
        thread.__init__(self, name = "LoRaWorker")

        self._loralock = _thread.allocate_lock()
        self._transmit_queue = queue()
        self._receive_queue = queue()

    def init(self):
        self._spi = SPI(baudrate=10000000, polarity=0, phase=0, bits=8, firstbit = SPI.MSB,
                        sck = Pin(_SX127x_SCK, Pin.OUT, Pin.PULL_DOWN),
                        mosi = Pin(_SX127x_MOSI, Pin.OUT, Pin.PULL_UP),
                        miso = Pin(_SX127x_MISO, Pin.IN, Pin.PULL_UP))

        self._ss = Pin(_SX127x_SS, Pin.OUT)
        self._reset = Pin(_SX127x_RESET, Pin.OUT)
        self._int_pin = Pin(_SX127x_INT, Pin.IN)

        # Perform base class init
        super().init(_SX127x_WANTED_VERSION)

        # Start the worker thread
        self.start()

    def run(self):
        # print("Worker running")
        while self.running:
            packet = self.receive_packet()
            if packet:
                print("Received: rssi %d '%s'" % (packet['rssi'], packet['data'].decode()))
                del(packet)
        # print("Worker exit")
        return 0

    # Reset device
    def reset(self):
        self._reset.value(0)
        sleep(0.1)
        self._reset.value(1)

    # Read register from SPI port
    def read_register(self, address):
        return int.from_bytes(self._spi_transfer(address & 0x7F), 'big')

    # Write register to SPI port
    def write_register(self, address, value):
        self._spi_transfer(address | 0x80, value)

    def _spi_transfer(self, address, value = 0):
        response = bytearray(1)
        self._ss.value(0)
        self._spi.write(bytes([address]))
        self._spi.write_readinto(bytes([value]), response)
        self._ss.value(1)
        return response

    # Read block of data from SPI port
    def read_buffer(self, address, length):
        response = bytearray(length)
        self._ss.value(0)
        self._spi.write(bytes([address & 0x7F]))
        self._spi.readinto(response)
        self._ss.value(1)
        return response

    # Write block of data to SPI port
    def write_buffer(self, address, buffer):
        self._ss.value(0)
        self._spi.write(bytes([address | 0x80]))
        self._spi.write(buffer)
        self._ss.value(1)

    def attach_interrupt(self, callback):
        self._int_pin.irq(handler=callback, trigger=Pin.IRQ_RISING if callback else 0)

    def onReceive(self, packet, crc_ok, rssi):
        # print("onReceive: crc_ok %s packet %s rssi %d" % (crc_ok, packet, rssi))
        if crc_ok:
            # Check addresses etc
            self._receive_queue.append({'rssi': rssi, 'data': packet })

    def receive_packet(self):
        return self._receive_queue.remove()

    # Finished transmitting - see if we can transmit another
    # If we have another packet, return it to caller.
    def onTransmit(self):
        packet = self._transmit_queue.remove(wait=0)
        del(packet)

        # print("onTransmit: queue has %d" % len(self._transmit_queue))

        # Returns None if nothing in queue
        return self._transmit_queue.remove(wait=0)

    # Put packet into transmit queue.  If queue was empty, start transmitting
    def send_packet(self, packet):
        with self._loralock:
            # print("Appending to queue")
            self._transmit_queue.append(packet)
            if len(self._transmit_queue) == 1:
                self.transmit_packet(packet)

    def __exit__(self):
        if self._spi:
            self._spi.deinit()
            self._spi = None

        self.stop()
        self._receive_queue.append(None)
        rc = self.wait()
        # print("Exit worker rc %d" % rc)

