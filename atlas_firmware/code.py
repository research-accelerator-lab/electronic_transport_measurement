import board
import usb_cdc
import busio
import adafruit_ssd1306
from time import sleep
from map_device import MAP
from atlas_device import ATLAS

WIDTH = 128
HEIGHT = 64
BORDER = 5

chips = [False, False, False]

serial = usb_cdc.data

dev_one_two_i2c = []
dev_three_home_i2c = []

try:
    i2c_one = busio.I2C(scl=board.GP5, sda=board.GP4)
    # a scan
    i2c_one.try_lock()
    dev_one_two_i2c = i2c_one.scan()
    i2c_one.unlock()
except:
    pass

try:
    i2c_two = busio.I2C(scl=board.GP7, sda=board.GP6)
    # a scan
    i2c_two.try_lock()
    dev_three_home_i2c = i2c_two.scan()
    i2c_two.unlock()
except:
    pass

print(dev_one_two_i2c, dev_three_home_i2c)

if 60 in dev_one_two_i2c:
    dev1_oled = adafruit_ssd1306.SSD1306_I2C(width=WIDTH, height=HEIGHT, i2c=i2c_one, addr=60)
    chips[0] = MAP(pins=(board.GP8, board.GP9, board.GP11, board.GP10, board.GP12), tty=serial, oled=dev1_oled, host=False)

if 61 in dev_one_two_i2c:
    dev2_oled = adafruit_ssd1306.SSD1306_I2C(width=WIDTH, height=HEIGHT, i2c=i2c_one, addr=61)
    chips[1] = MAP(pins=(board.GP13, board.GP14, board.GP16, board.GP15, board.GP17), tty=serial, oled=dev2_oled, host=False)

if 61 in dev_three_home_i2c:
    dev3_oled = adafruit_ssd1306.SSD1306_I2C(width=WIDTH, height=HEIGHT, i2c=i2c_two, addr=61)
    chips[2] = MAP(pins=(board.GP18, board.GP19, board.GP21, board.GP20, board.GP22), tty=serial, oled=dev3_oled, host=False)

atlas_oled = adafruit_ssd1306.SSD1306_I2C(width=WIDTH, height=HEIGHT, i2c=i2c_two, addr=60)
atlas = ATLAS(pins=(board.GP0, board.GP1, board.GP2, board.GP3, board.GP27, board.GP26), tty=serial, oled=atlas_oled, chips=chips)

in_data = bytearray()

while True:
    # Check for incoming data
    if serial.in_waiting > 0:
        byte = serial.read(1)
        if byte == b'\n':
            atlas.process_serial(in_data.decode("utf-8"))
            out_data = in_data
            out_data += b'  '
            in_data = bytearray()
            out_index = 0
        else:
            in_data += byte
            if len(in_data) == 129:
                in_data = in_data[128] + in_data[1:127]

    atlas.led.value = not atlas.led.value
    sleep(.1)
