import board
import usb_cdc
import busio
import adafruit_ssd1306
from time import sleep
from map_device import MAP

# display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
# display_bus2 = displayio.I2CDisplay(si2c, device_address=0x3D)
WIDTH = 128
HEIGHT = 64
BORDER = 5

serial = usb_cdc.data

i2c_one = busio.I2C(scl=board.GP5, sda=board.GP4)
# a scan
i2c_one.try_lock()
dev_id = i2c_one.scan()[0]
i2c_one.unlock()
# i2c.deinit()

oled = adafruit_ssd1306.SSD1306_I2C(width=WIDTH, height=HEIGHT, i2c=i2c_one, addr=dev_id)

chip = MAP(pins=(board.GP0, board.GP1, board.GP3, board.GP2, board.GP28), tty=serial, oled=oled, host=True)

in_data = bytearray()

while True:
    # Check for incoming data
    if serial.in_waiting > 0:
        byte = serial.read(1)
        if byte == b'\n':
            #log(in_data.decode("utf-8"))
            chip.process_serial(in_data.decode("utf-8"))
            out_data = in_data
            out_data += b'  '
            in_data = bytearray()
            out_index = 0
        else:
            in_data += byte
            if len(in_data) == 129:
                in_data = in_data[128] + in_data[1:127]

    chip.led.value = not chip.led.value
    sleep(.1)
