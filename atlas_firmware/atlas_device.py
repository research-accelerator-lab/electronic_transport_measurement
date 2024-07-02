import digitalio
import board


class ATLAS():

    def __init__(self, pins, tty, oled, chips=(False, False, False)):
        self.pins = []
        for idx, i in enumerate(pins):
            self.pins.append(digitalio.DigitalInOut(i))
            self.pins[idx].direction = digitalio.Direction.OUTPUT
            self.pins[idx].value = False

        self.tty = tty
        self.oled = oled

        self.led = digitalio.DigitalInOut(board.LED)
        self.led.direction = digitalio.Direction.OUTPUT
        self.led.value = True

        self.chips = chips
        self.cur_device = None
        self.cur_config = None
        self.cur_idx = None
        self.mobo_flip = False
        self.draw(setup=True)
        if self.chips[0]:
            self.cur_idx = 0
            self.cur_device = self.chips[0]
            self.cur_config = ('1', '0')
            self.cur_device.draw(self.cur_config, mobo_flip=False)
            self.draw()

    def draw(self, setup=False):
        self.oled.fill(0)

        text = ['CHIP 1: N/A', 'CHIP 2: N/A', 'CHIP 3: N/A']

        for cdx, chip in enumerate(self.chips):
            if chip:
                if cdx == self.cur_idx and not setup:
                    text[cdx] = 'CHIP ' + str(cdx + 1) + ': TESTING'
                else:
                    text[cdx] = 'CHIP ' + str(cdx + 1) + ': READY'
                    self.draw_chip_state(chip, text[cdx])

        self.oled.text('VDP MOBO', 0, 0, 'black')
        self.oled.text(text[0], 5, 18, 'black')
        self.oled.text(text[1], 5, 34, 'black')
        self.oled.text(text[2], 5, 53, 'black')
        self.oled.show()

    def draw_chip_state(self, chip, text='ERR'):
        chip.oled.fill(0)
        chip.oled.text(text, 0, 0, 'black')
        chip.oled.show()

    def process_serial(self, cmd):
        cmd = cmd.split('.')
        mask = []
        self.mobo_flip = False
        if cmd[0] == "CONFIG" and len(cmd) == 5:
            print(cmd)
            dev = cmd[1]
            conf = cmd[2]
            # if VDPChip is present
            dev_index = int(dev) - 1

            if dev_index < 3 and self.chips[dev_index]:
                # set device to "TESTING" state
                if dev == '1':
                    if conf == '0':
                        mask = [False, False, False, False, False, False]
                    elif conf == '1':
                        self.mobo_flip = True
                        mask = [False, False, True, False, False, False]
                elif dev == '2':
                    if conf == '0':
                        mask = [True, False, False, False, False, True]
                    elif conf == '1':
                        self.mobo_flip = True
                        mask = [True, False, False, True, False, True]
                elif dev == '3':
                    if conf == '0':
                        mask = [True, True, False, False, True, False]
                    elif conf == '1':
                        self.mobo_flip = True
                        mask = [True, True, False, True, True, False]

            if len(mask):
                if self.cur_idx != dev_index:
                    if self.cur_device:
                        for p in self.cur_device.pins:
                            p.value = False

                    self.cur_idx = dev_index
                    self.cur_device = self.chips[self.cur_idx]

                for idx, i in enumerate(mask):
                    self.pins[idx].value = i

                dev_conf = (cmd[3], cmd[4])
                self.draw()
                self.cur_device.process_command(dev_conf, mobo_flip=self.mobo_flip)

        else:
            self.tty.write(b"BAD INPUT")
