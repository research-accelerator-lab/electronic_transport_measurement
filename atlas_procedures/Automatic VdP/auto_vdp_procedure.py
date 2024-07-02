# Import necessary packages
from pymeasure.instruments.keithley import Keithley2400, Keithley2600
from pymeasure.experiment import Procedure
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter
from pymeasure.adapters import SerialAdapter

# Import ATLAS instrument control
from atlas_driver import ATLAS

from time import sleep, time
import logging
import math
import numpy as np
import sys
import glob
import serial

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Finding the USB port ATLAS is connected to
def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


print(serial_ports())

class AutoVdpProcedure(Procedure):
    
    # For identification:
    # wafer_id = ListParameter('Wafer ID', choices=['01A', '02A', '03A', '04A', '05A', '06A', '07A', '08A'])
    # map_1_chip_id = ListParameter('Map 1 Chip ID', choices=['01','02', '03', '04', '05', '06', '07', '08'])    
    # map_2_chip_id = ListParameter('Map 2 Chip ID', choices=['01','02', '03', '04', '05', '06', '07', '08'])    
    # map_3_chip_id = ListParameter('Map 3 Chip ID', choices=['01','02', '03', '04', '05', '06', '07', '08'])    
    # study_id = Parameter('Study ID', default='S1')
    wafer_id = Parameter('Wafer ID', default='##')
    map_1_chip_id = Parameter('Map 1 Chip ID', default='##')    
    map_2_chip_id = Parameter('Map 2 Chip ID', default='##')    
    map_3_chip_id = Parameter('Map 3 Chip ID', default='##')  
    study_id = Parameter('Study ID', default='S#')
    
    #For the Keithley 2400
    vdp_start_current = FloatParameter('VdP Start I', units='A', default=1E-8)
    vdp_stop_current = FloatParameter('VdP Stop I', units='A', default=1E-6)
    vdp_current_num = IntegerParameter('VdP I Number of Steps', default=5.)
    
    vdp_delay = FloatParameter('VdP Measurement Delay', units='s', default=1)
    
    #For the Keithley 2611
    gate_start_voltage = FloatParameter('Gate Start V', units='V', default=60.)
    gate_stop_voltage = FloatParameter('Gate Stop V', units='V', default=120.)
    gate_voltage_num = IntegerParameter('Gate V Number of Steps', default=4.)

    #Info for ATLAS
    atlas_addr = Parameter('ATLAS Address', default='COM3')
    atlas_config = IntegerParameter('ATLAS Config', default=0)
    device = IntegerParameter('Device', default=1)
    map_id = IntegerParameter('MAP', default=1)
    map_config = IntegerParameter('MAP Config', default=0)
    
    # Defining data columns
    DATA_COLUMNS = ['timestamp','Gate Voltage (V)','Gate Current (A)','VdP Current (A)', 'VdP Voltage Positive (V)', 
                    'VdP Voltage Negative (V)', 'Thermoelectric Offset (V)', 'VdP Voltage (V)', 'Resistance (ohm)']

    K2400sourcemeter = None
    K2611sourcemeter = None
    atlas = None
    adapter = None
    timer = 0.0

    def startup(self):

        print('CONNECTING TO ATLAS')
        self.adapter = SerialAdapter(self.atlas_addr, write_termination="\n", read_termination="\n")
        self.atlas = ATLAS(self.adapter)

        print('ATLAS ON')

        print('STARTING 2611')

        self.K2611sourcemeter = Keithley2600("USB0::0x05E6::0x2611::4025115::INSTR")
        self.K2611sourcemeter.reset()
        self.K2611sourcemeter.ChA.source_output = 'OFF'
        self.K2611sourcemeter.ChA.apply_voltage(voltage_range=None, compliance_current=0.01)
        self.K2611sourcemeter.ChA.measure_current(nplc=1, auto_range=True)
        self.K2611sourcemeter.ChA.wires_mode = '2'
        self.K2611sourcemeter.ChA.source_output = 'ON'
        self.K2611sourcemeter.ChA.source_voltage = 0
        
        print("2611 ON")

        print("STARTING 2400")

        self.K2400sourcemeter = Keithley2400("GPIB0::20::INSTR",timeout=10000, open_timeout=10000)
        self.K2400sourcemeter.reset()
        print(self.K2400sourcemeter.adapter.connection.timeout)
        self.K2400sourcemeter.use_front_terminals()
        self.K2400sourcemeter.write(":source:clear:immediate")
        self.K2400sourcemeter.apply_current(current_range=None, compliance_voltage=20)
        self.K2400sourcemeter.auto_zero = 1
        self.K2400sourcemeter.source_delay_auto = True
        self.K2400sourcemeter.measure_voltage(nplc=1, auto_range=True)
        self.K2400sourcemeter.filter_type = 'REP'
        self.K2400sourcemeter.filter_count = 3
        self.K2400sourcemeter.filter_state = 'ON'
        self.K2400sourcemeter.wires = 4
        self.K2400sourcemeter.enable_source()

        print("2400 ON")

    def execute(self):

        print("EXECUTE")

        # Defining gate voltage array from input values
        if self.gate_voltage_num == 0:
            gate_voltages = [self.gate_start_voltage]
        else:
            gate_voltages_up = np.linspace(self.gate_start_voltage, self.gate_stop_voltage,
                                           self.gate_voltage_num)
            #gate_voltages_down = list(reversed(gate_voltages_up[:-1]))
            #gate_voltages = list(gate_voltages_up) + gate_voltages_down
            gate_voltages = list(gate_voltages_up)
        print('gate voltages:', gate_voltages)

       # Defining vdp voltage array from input values
        if self.vdp_start_current > 0:
            vdp_currents = np.logspace(math.log10(self.vdp_start_current), math.log10(self.vdp_stop_current), self.vdp_current_num)
        elif self.vdp_start_current < 0:
            vdp_currents = np.logspace(math.log10(-self.vdp_start_current), math.log10(-self.vdp_stop_current), self.vdp_current_num)
            vdp_currents = [-i for i in vdp_currents]
            
        print('vdp currents:', vdp_currents)

        # Stabilizing instruments
        print('Starting experiment!')
        sleep(1)  
        self.atlas.config = (self.map_id, self.atlas_config, self.device, self.map_config)
        sleep(1)
        self.K2611sourcemeter.ChA.source_current = 0
        sleep(1)
        self.K2400sourcemeter.source_voltage = 0
        sleep(1)
        print("ATLAS CONFIG:", self.atlas_config, "MAP ID:", self.map_id, "MAP CONFIG:", self.map_config, "DEVICE:", self.device)

        start_time = time()
        
        for gate_vdx, gate_volt in enumerate(gate_voltages):

            self.K2611sourcemeter.ChA.source_voltage = gate_volt
            sleep(self.vdp_delay)  # stabilization time

            for vdp_idx, vdp_cur in enumerate(vdp_currents):
                
                self.K2400sourcemeter.source_current = vdp_cur
                sleep(self.vdp_delay) # time when measurement is taken after vdp voltage applied
                
                
                try:
                    vdp_volt_pos = self.K2400sourcemeter.voltage
                except Exception as e:
                    print("timeout on vdp_volt_pos:")
                    print(e)
                    continue
                
                self.K2400sourcemeter.source_current = -vdp_cur
                sleep(self.vdp_delay) # time when measurement is taken after vdp voltage applied
                
                try:
                    vdp_volt_neg = self.K2400sourcemeter.voltage
                except Exception as e:
                    print("timeout on vdp_volt_neg:")
                    print(e)
                    continue
                
                
                vdp_volt = (vdp_volt_pos-vdp_volt_neg)/2
                                    
                #DATA_COLUMNS = ['timestamp','device','configuration', 'Gate Voltage (V)','Gate Current (A)','VdP Voltage (V)', 'VdP Current (A)', 'Resistance']
                data = {'timestamp': round(time() - start_time, 3),
                        'Gate Voltage (V)': gate_volt,
                        'Gate Current (A)': self.K2611sourcemeter.ChA.current,
                        'VdP Current (A)': vdp_cur,
                        'VdP Voltage Positive (V)': vdp_volt_pos,
                        'VdP Voltage Negative (V)': vdp_volt_neg,
                        'VdP Voltage (V)': vdp_volt,
                        'Thermoelectric Offset (V)': (vdp_volt_pos-vdp_volt),
                        'Resistance (ohm)': abs(vdp_volt/vdp_cur)}
                
                self.emit('results', data)
                self.emit('progress', 100.*((gate_vdx)*len(vdp_currents)+(vdp_idx+1))/(len(gate_voltages)*len(vdp_currents)))
                

                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    break
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break

    def shutdown(self):
        self.K2611sourcemeter.ChA.shutdown()
        self.K2400sourcemeter.shutdown()
        self.adapter.close()
        print("Done")