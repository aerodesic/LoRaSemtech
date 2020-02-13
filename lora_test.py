#
# LoRa message driver.
#

from time import sleep
from ulock import *
from uqueue import *
from uthread import *
from sx127x import *
from machine import SPI, Pin


_SX127x_INT   = const(26)   # Interrupt pin
_SX127x_SCK   = const(5)
_SX127x_MOSI  = const(27)
_SX127x_MISO  = const(19)
_SX127x_SS    = const(18)
_SX127x_RESET = const(14)
_SX127x_WANTED_VERSION = const(0x12)
_BUTTON_PIN   = const(0)
_LED_PIN      = const(25)

class LoRaHandler(SX127x_driver):

    def __init__(self, packet_delay=0, display = None):
        # SX127x_driver.__init__(self, bandwidth=50e3, spreading_factor=10)
        SX127x_driver.__init__(self, tx_power=17, enable_crc=True, hop_period=1)

        self._packet_delay = packet_delay
        self._loralock = rlock()
        self._transmit_queue = queue()
        self._receive_queue = queue()
        self._display = display if display else lambda text,line=0,clear=False : None

    def init(self):
        self._spi = SPI(baudrate=10000000, polarity=0, phase=0, bits=8, firstbit = SPI.MSB,
                        sck = Pin(_SX127x_SCK, Pin.OUT, Pin.PULL_DOWN),
                        mosi = Pin(_SX127x_MOSI, Pin.OUT, Pin.PULL_UP),
                        miso = Pin(_SX127x_MISO, Pin.IN, Pin.PULL_UP))

        self._ss = Pin(_SX127x_SS, Pin.OUT)
        self._reset = Pin(_SX127x_RESET, Pin.OUT)
        self._int_pin = Pin(_SX127x_INT, Pin.IN)
        self._button = Pin(_BUTTON_PIN, Pin.IN)
        self._button_flag = lock(True)
        self._ping_count = 0
        self._led_pin = Pin(_LED_PIN, Pin.OUT)
        self._power = None # not True nor False

        # Perform base class init
        super().init(_SX127x_WANTED_VERSION)

        self._display("Ready", clear=True)


        # Start the worker thread
        self._worker_thread = thread(run=self._worker_run, name="worker_thread", stack=8192)
        self._worker_thread.start()
        
        self._button_thread = thread(run=self._button_run, name="button_thread", stack=8192)
        self._button_thread.start()

        # Set power state for button and control
        self.set_power()

    # Interrupt comes here
    def _button_pressed(self, event=None):
        try:
            self._button_flag.release()
        except:
            pass

    def _button_run(self, t):
        while self._button_flag.acquire() and t.running:
            # print("Button pressed")
            self._ping_count += 1
            self._display("ping %d" % (self._ping_count))
            # Launch a ping message
            self.send_packet(b'ping %d' % self._ping_count)

    def _worker_run(self, t):
        # print("Worker running")
        while t.running:
            packet = self.receive_packet()
            if packet:
                rssi = packet['rssi']
                data = packet['data'].decode()
                # print("Received: rssi %d '%s'" % (rssi, data))
                gc.collect()
                self._led_pin.on()
                sleep(0.1)
                self._led_pin.off()
                if packet['data'][0:5] == b'ping ':
                    # Send answer
                    self.send_packet(b'reply %s (%d)' % (data[5:], rssi))
                else:
                    self._display("(%d) %s" % (rssi, data), line=2, clear=False)
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
    def write_buffer(self, address, buffer, size):
        self._ss.value(0)
        self._spi.write(bytes([address | 0x80]))
        self._spi.write(memoryview(buffer)[0:size])
        self._ss.value(1)

    def attach_interrupt(self, callback):
        self._int_pin.irq(handler=callback, trigger=Pin.IRQ_RISING if callback else 0)

    def onReceive(self, packet, crc_ok, rssi):
        # print("onReceive: crc_ok %s packet %s rssi %d" % (crc_ok, packet, rssi))
        if crc_ok:
            # Check addresses etc
            self._receive_queue.put({'rssi': rssi, 'data': packet })

    def receive_packet(self):
        return self._receive_queue.get()

    # Finished transmitting - see if we can transmit another
    # If we have another packet, return it to caller.
    def onTransmit(self):
        # Delete top packet in queue
        packet = self._transmit_queue.get(wait=0)
        del packet

        # Return head of queue.
        return self._transmit_queue.head()

    # Put packet into transmit queue.  If queue was empty, start transmitting
    def send_packet(self, packet):
        with self._loralock:
            # print("Appending to queue: %s" % packet.decode())
            self._transmit_queue.put(packet)
            if len(self._transmit_queue) == 1:
                self.transmit_packet(packet)

        if self._packet_delay:
            sleep(self._packet_delay)

    def close(self):
        print("LoRa handler close called")
        super().close()
        if self._spi:
            self._spi.deinit()
            self._spi = None

        self.set_power(False)

        if self._worker_thread:
            self._worker_thread.stop()
            self._receive_queue.put(None)
            rc = self._worker_thread.wait()
            print("Exit %s rc %d" % (self._worker_thread.name(), rc))
            self._worker_thread = None

        if self._button_thread:
            self._button_thread.stop()
            try:
                self._button_flag.release()
            except:
                pass
            self._button_thread.wait()
            self._button_thread = None

    def set_power(self, power=True):
        # print("set_power %s" % power)

        if power != self._power:
            self._power = power

            # Call base class
            super().set_power(power)

            if power:
                self._button.irq(handler=self._button_pressed, trigger=Pin.IRQ_FALLING)
            else:
                self._button.irq(handler=None, trigger=0)
                self._display("Ready" if power else "", clear=True)

    def __del__(self):
        self.close()


