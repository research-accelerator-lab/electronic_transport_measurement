import digitalio
import board

class MAP():

    def __init__(self, pins, tty, oled, host=True):
        self.pins = []
        for idx, i in enumerate(pins):
            self.pins.append(digitalio.DigitalInOut(i))
            self.pins[idx].direction = digitalio.Direction.OUTPUT
            self.pins[idx].value = False

        self.tty = tty
        self.oled = oled
        self.led = None

        if host:
            self.draw(('1', '0'))
            self.led = digitalio.DigitalInOut(board.LED)
            self.led.direction = digitalio.Direction.OUTPUT
            self.led.value = True

    def draw(self, config, mobo_flip=False):
        num = config[0]
        conf = config[1]
        self.oled.fill(0)

        top_left = 'ERR'
        bot_right = 'ERR'
        top_right = 'I HI'
        bot_left = 'V LO'

        if conf == '0':
            top_left = 'I LO'
            bot_right = 'V HI'
        elif conf == '1':
            top_left = 'V HI'
            bot_right = 'I LO'

        if mobo_flip:
            top_right = 'V LO'
            bot_left = 'I HI'
        right_x = 15
        left_x = 5
        right_y = 20
        left_y = 25
        self.oled.text('DEVICE: ' + num, 0, 0, 'black', size=2)
        self.oled.fill_rect(50, 23, 16, 23, 1)

        self.oled.text(top_left, 5, 20, 'black')
        self.oled.hline(40, 20, right_x, right_y)
        self.oled.vline(55, 20, left_x, left_y)

        self.oled.text(top_right, 80, 20, 'black')
        self.oled.hline(60, 20, right_x, right_y)
        self.oled.vline(60, 20, left_x, left_y)

        self.oled.text(bot_left, 5, 45, 'black')
        self.oled.hline(40, 49, right_x, right_y)
        self.oled.vline(54, 45, left_x, left_y)

        self.oled.text(bot_right, 80, 45, 'black')
        self.oled.hline(60, 49, right_x, right_y)
        self.oled.vline(60, 45, left_x, left_y)
        self.oled.show()

    def process_serial(self, cmd):
        cmd = cmd.split('.')
        if cmd[0] == "DEV" and len(cmd) == 3:
            # Format "DEV.1.0"
            dev_conf = (cmd[1], cmd[2])
            self.process_command(dev_conf)
        else:
            self.tty.write(b"BAD INPUT")

    def process_command(self, cmd, mobo_flip=False):
        mask = []
        dev = cmd[0]
        conf = cmd[1]
        if dev == '1':
            if conf == '0':
                mask = [False, False, False, False, False]
            elif conf == '1':
                mask = [False, False, False, True, False]
        elif dev == '2':
            if conf == '0':
                mask = [False, True, False, True, False]
            elif conf == '1':
                mask = [False, True, False, False, False]
        elif dev == '3':
            if conf == '0':
                mask = [True, False, False, False, True]
            elif conf == '1':
                mask = [True, False, False, False, False]
        elif dev == '4':
            if conf == '0':
                mask = [True, False, True, False, False]
            elif conf == '1':
                mask = [True, False, True, False, True]

        if len(mask) and cmd:
            for idx, i in enumerate(mask):
                self.pins[idx].value = i

            self.draw(cmd, mobo_flip)
        else:
            self.tty.write(b"BAD INPUT")