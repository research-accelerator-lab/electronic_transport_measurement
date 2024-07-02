# Import necessary packages
from pymeasure.instruments.keithley import Keithley2400, Keithley2600
from pymeasure.experiment import Procedure
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter, ListParameter
from pymeasure.adapters import SerialAdapter

# Import ATLAS instrument control
from atlas_driver import ATLAS

from time import sleep, time
import logging
import numpy as np
import sys
import glob
import serial
import statistics

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

class AutoVdpProcedure_SweepVg(Procedure):
    
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
    
    #For the Keithley 2611
    gate_voltage_start = FloatParameter('Vg Start', units='V', default=0)
    gate_voltage_end = FloatParameter('Vg End', units='V', default=120)
    gate_voltage_step = FloatParameter('Vg Step', units='V', default=1)
    gate_voltage_sweep_rate = FloatParameter('Vg Sweep Rate', units='V/s', default=2)
    
    #Input from the sequencer for the Keithley 2400
    vdp_cur = FloatParameter('VdP Current (A)', default=1E-7)

    #Info for ATLAS
    atlas_addr = Parameter('ATLAS Address', default='COM3')
    atlas_config = IntegerParameter('ATLAS Config', default=0)
    device = IntegerParameter('Device', default=1)
    map_id = IntegerParameter('MAP', default=1)
    map_config = IntegerParameter('MAP Config', default=0)
    
    # sourcemeter settings
    setting_nplc = ListParameter('Sourcemeter NPLC Setting', choices=[0.1, 1., 10.], default = 0.1)  # 0.1 for fast, 1 for normal, 10 for slow
    setting_filter = ListParameter('Sourcemeter Filter Setting', choices=['ON', 'OFF'], default = 'OFF')
    
    # Defining data columns
    DATA_COLUMNS = ['timestamp', 'Gate Voltage (V)', 'Gate Current (A)', 'VdP Current (A)', 
                    'VdP Voltage (V)', 'Resistance (ohm)']

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
        self.K2611sourcemeter.ChA.measure_current(nplc=self.setting_nplc, auto_range=True)
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
        self.K2400sourcemeter.measure_voltage(nplc=self.setting_nplc, auto_range=True)
        self.K2400sourcemeter.filter_type = 'REP'
        self.K2400sourcemeter.filter_count = 3
        self.K2400sourcemeter.filter_state = self.setting_filter
        self.K2400sourcemeter.wires = 4
        self.K2400sourcemeter.enable_source()

        print("2400 ON")

    def execute(self):

        print("EXECUTE")

        # Defining gate voltage array from input values
        gate_voltage_up = np.arange(self.gate_voltage_start, self.gate_voltage_end, self.gate_voltage_step)
        gate_voltage_down = np.arange(self.gate_voltage_end, self.gate_voltage_start, -self.gate_voltage_step)
        gate_voltages = np.concatenate((gate_voltage_up, gate_voltage_down))
        print('gate_voltages: ', gate_voltages)
        
        # Defining the delay between measurements based on the desired voltage step and sweep rate
        delay = abs(self.gate_voltage_step/self.gate_voltage_sweep_rate)
        print("delay is", delay, "s")

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

        # Apply vdp current
        vdp_curr = self.vdp_cur
        self.K2400sourcemeter.source_current = vdp_curr
        sleep(3) 
        
        start_time = time()
        real_sweep_rate = []
        
        
        for gate_vdx, gate_volt in enumerate(gate_voltages):
            
            meas_start = time()
                
            # Apply gate voltage
            self.K2611sourcemeter.ChA.source_voltage = gate_volt
            
            # Measuring parameters
            
            try:
                vdp_volt = self.K2400sourcemeter.voltage
            except Exception as e:
                print("timeout on vdp_volt")
                print(e)
                continue
            
            gate_cur = self.K2611sourcemeter.ChA.current
            
            #DATA_COLUMNS = ['timestamp', 'Gate Voltage (V)','Gate Current (A)', 'VdP Current (A)', 'VdP Voltage (V)', 'Resistance (V/A)']
            data = {'timestamp': round(time() - start_time, 3),
                    'Gate Voltage (V)': gate_volt,
                    'Gate Current (A)': gate_cur,
                    'VdP Current (A)': vdp_curr,
                    'VdP Voltage (V)': vdp_volt,
                    'Resistance (ohm)': abs(vdp_volt/vdp_curr)}
            
            self.emit('results', data)
            self.emit('progress', 100*(gate_vdx+1)/(len(gate_voltages)))
            
            # pause between measurements to achieve desired sweeprate
            meas_end = time()
            sleep_time = delay - (meas_end-meas_start)
            if sleep_time > 0:
                sleep(sleep_time)
                real_sweep_rate.append(self.gate_voltage_step/(meas_end-meas_start+sleep_time))
            else:
                real_sweep_rate.append(self.gate_voltage_step/(meas_end-meas_start))
                print('sweep rate is too fast or resolution too small!')
                
            
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break
            
        print('real sweep rate was:', round(statistics.mean(real_sweep_rate),3), 'V/s')
            
            

    def shutdown(self):
        self.K2611sourcemeter.ChA.shutdown()
        self.K2400sourcemeter.shutdown()
        self.adapter.close()
        print("Done")