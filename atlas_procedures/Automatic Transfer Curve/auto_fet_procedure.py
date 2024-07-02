# Import necessary packages
from pymeasure.instruments.keithley import Keithley2400, Keithley2600
from pymeasure.experiment import Procedure
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter
from pymeasure.adapters import SerialAdapter

# Import ATLAS instrument control
from atlas_driver import ATLAS

from time import sleep, time
import logging
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


class AutoFETProcedure(Procedure):

    # For identification:
    #wafer_id = ListParameter('Wafer ID', choices=['01A', '02A', '03A', '04A', '05A', '06A', '07A', '08A'])
    #map_1_chip_id = ListParameter('Map 1 Chip ID', choices=['09', '10', '11', '12', '13', '14', '15', '16'])    
    #map_2_chip_id = ListParameter('Map 2 Chip ID', choices=['09', '10', '11', '12', '13', '14', '15', '16'])    
    #map_3_chip_id = ListParameter('Map 3 Chip ID', choices=['09', '10', '11', '12', '13', '14', '15', '16'])    
    wafer_id = Parameter('Wafer ID', default='##')
    map_1_chip_id = Parameter('Map 1 Chip ID', default='##')    
    map_2_chip_id = Parameter('Map 2 Chip ID', default='##')    
    map_3_chip_id = Parameter('Map 3 Chip ID', default='##')  
    study_id = Parameter('Study ID', default='S#')

    # For the Keithley 2400
    V_d = FloatParameter('Drain V', units='V', default=0.1)
    
    # For the Keithley 2611
    V_g_start = FloatParameter('Vg Start', units='V', default=-20)
    V_g_end = FloatParameter('Vg End', units='V', default=60)
    V_g_step = FloatParameter('Vg Step', units='V', default=1)
    V_g_sweep_rate = FloatParameter('Vg Sweep Rate', units='V/s', default=2)

    #Info for ATLAS
    atlas_addr = Parameter('ATLAS Address', default='COM3')
    atlas_config = IntegerParameter('ATLAS Config', default=0)
    device = IntegerParameter('Device', default=1)
    map_id = IntegerParameter('MAP', default=1)
    map_config = IntegerParameter('MAP Config', default=0)
    
    # Defining data columns
    DATA_COLUMNS = ['timestamp','Gate Voltage (V)', 'Gate Current (A)', 'Drain Current (A)', 'abs(Drain Current) (A)']
    
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
        self.K2611sourcemeter.ChA.apply_voltage(voltage_range=None,compliance_current=0.01)
        self.K2611sourcemeter.ChA.measure_current(nplc=1, auto_range=True)
        self.K2611sourcemeter.ChA.wires_mode = '2'
        self.K2611sourcemeter.ChA.source_output = 'ON'
        self.K2611sourcemeter.ChA.source_voltage = 0
        
        print("2611 ON")
        
        print("STARTING 2400")
        
        self.K2400sourcemeter = Keithley2400("GPIB0::20::INSTR",timeout=10000, open_timeout=10000)
        self.K2400sourcemeter.reset()
        
        self.K2400sourcemeter.use_front_terminals()
        self.K2400sourcemeter.write(":source:clear:immediate")
        self.K2400sourcemeter.apply_voltage(voltage_range=None, compliance_current=0.01)
        self.K2400sourcemeter.auto_zero = 1
        self.K2400sourcemeter.source_delay_auto = True
        self.K2400sourcemeter.measure_current(nplc=1, auto_range=True)
        self.K2400sourcemeter.filter_type = 'REP'
        self.K2400sourcemeter.filter_count = 3
        self.K2400sourcemeter.filter_state = 'ON'
        self.K2400sourcemeter.wires = 2
        self.K2400sourcemeter.enable_source()

        print("2400 ON")
        
    def execute(self):
        
        print("EXECUTE")
        
        # Defining gate voltage array from input values
        V_g_up = np.arange(self.V_g_start, self.V_g_end, self.V_g_step)
        V_g_down = np.arange(self.V_g_end, self.V_g_start, -self.V_g_step)
        V_g_array = np.concatenate((V_g_up, V_g_down))
        
        # Defining the delay between measurements based on the desired voltage step and sweep rate
        delay = abs(self.V_g_step/self.V_g_sweep_rate)
        print("delay is", delay, "s")
        
        # Stabilizing instruments
        print('Starting experiment!')
        sleep(1)  
        self.atlas.config = (self.map_id, self.atlas_config, self.device, self.map_config)
        sleep(1)
        self.K2611sourcemeter.ChA.source_voltage = 0 
        sleep(1)
        self.K2400sourcemeter.source_voltage = 0
        sleep(1)
        print("ATLAS CONFIG:", self.atlas_config, "MAP ID:", self.map_id, "MAP CONFIG:", self.map_config, "DEVICE:", self.device)

        start_time = time()
            
        for step, V_g in enumerate(V_g_array):
            
             # Apply drain voltage
            self.K2400sourcemeter.source_voltage = self.V_d

            # Apply gate voltage
            self.K2611sourcemeter.ChA.source_voltage = V_g
            
            I_d = self.K2400sourcemeter.current
            
            # Collecting data
            # DATA_COLUMNS = ['timestamp','Gate Voltage (V)', 'Gate Current (A)', 'Drain Current (A)','Source Current (A)']
            data = {'timestamp': round(time() - start_time, 3),
                 'Gate Voltage (V)': V_g,
                 'Gate Current (A)': self.K2611sourcemeter.ChA.current,
                 'Drain Current (A)': I_d,
                 'abs(Drain Current) (A)': abs(I_d)}
                
            self.emit('results', data)
            self.emit('progress', 100.*(step+1)/len(V_g_array))
            
            sleep(delay) # pause between measurements to achieve desired sweeprate
                
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break
        
                
    def shutdown(self):
        self.K2611sourcemeter.ChA.shutdown()
        self.K2400sourcemeter.shutdown()
        self.adapter.close()
        print("Done")