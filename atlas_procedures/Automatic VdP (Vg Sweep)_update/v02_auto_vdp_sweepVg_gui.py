# Importing necessary packages
from pymeasure.experiment.results import replace_placeholders
from pymeasure.experiment import Results
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow
from pymeasure.display.Qt import QtWidgets

import os
import sys
from datetime import datetime
import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

from v02_auto_vdp_sweepVg_procedure import v02_AutoVdpProcedure_SweepVg

# Defining function for naming files
def unique_filename(directory, prefix='DATA', suffix='', ext='csv',
                    dated_folder=False, index=True, datetimeformat="%Y-%m-%d",
                    procedure=None):
    """ Returns a unique filename based on the directory and prefix
    """
    now = datetime.now()
    directory = os.path.abspath(directory)

    if procedure is not None:
        prefix = replace_placeholders(prefix, procedure)
        suffix = replace_placeholders(suffix, procedure)

    if dated_folder:
        directory = os.path.join(directory, now.strftime('%Y-%m-%d'))
    if not os.path.exists(directory):
        os.makedirs(directory)
    if index:
        i = 1
        basename = f"{prefix}{now.strftime(datetimeformat)}"
        basepath = os.path.join(directory, basename)
        filename = "%s_%s%s.%s" % (basepath,  suffix, str(i).zfill(2), ext)
        while os.path.exists(filename):
            i += 1
            filename = "%s_%s%s.%s" % (basepath, suffix,  str(i).zfill(2), ext)
    else:
        basename = f"{prefix}{now.strftime(datetimeformat)}{suffix}.{ext}"
        filename = os.path.join(directory, basename)
    return filename


class MainWindow(ManagedDockWindow):
    
    def __init__(self):
        
        boxes = ['atlas_addr', 'study_id', 'wafer_id','map_1_chip_id','map_2_chip_id', 'map_3_chip_id',
                 'gate_voltage_start', 'gate_voltage_end','gate_voltage_sweep_rate','vdp_cur',
                 'setting_filter','VdP_voltage_range','G_current_range']
        
        super(MainWindow, self).__init__(
            procedure_class=v02_AutoVdpProcedure_SweepVg,
            inputs=boxes,
            displays=boxes,

            x_axis=['Gate Voltage (V)', 'Gate Voltage (V)'],
            y_axis=['Gate Current (A)', 'VdP Voltage (V)'],
            sequencer=True,                                      
            sequencer_inputs=['map_id', 'atlas_config', 'device', 'map_config','vdp_cur'],
            sequence_file="device_sequence.txt"
            
        )
        
        self.setWindowTitle('Automated VdP - Sweep Vg')


    def queue(self, procedure=None):
        
        if procedure is None:
            procedure = self.make_procedure()
            
        # Finding Paramteres form Procedure 
        device = str(procedure.device)
        map_id = str(procedure.map_id)
        atlas_config = str(procedure.atlas_config)
        map_config = str(procedure.map_config)
        
        study_id = str(procedure.study_id)
        wafer_id = str(procedure.wafer_id)

        # Identifying Chip 
        if map_id == '1':
            chip_id = str(procedure.map_1_chip_id)
        elif map_id == '2':
            chip_id = str(procedure.map_2_chip_id)
        elif map_id == '3':
            chip_id = str(procedure.map_3_chip_id)
        
        # Identifying Configuration
        if atlas_config == '0' and map_config == '0':
            main_config = '01'
        elif atlas_config == '0' and map_config == '1':
            main_config = '02'
        elif atlas_config == '1' and map_config == '0':
            main_config = '03'
        elif atlas_config == '1' and map_config == '1':
            main_config = '04'
        
        # Naming File
        if study_id =='S1':
            directory = r"Z:\projmon\vdp-fet-board-data\Study 1\\" + study_id + "_" + wafer_id + '\\vdp - sweep Vg\\raw_files'       
        else:
            directory = r"Z:\projmon\vdp-fet-board-data\Study " + study_id[-1] +"\\" + study_id + "_" + wafer_id + '\\vdp - sweep Vg\\raw_files'
        
        prefix = study_id + "_" + wafer_id + "_chip" + chip_id + "_device" + device.zfill(2) + "_config" + main_config
        
        filename = unique_filename(directory, prefix=prefix, suffix="trial", ext='csv', datetimeformat="")
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)
        
        self.manager.queue(experiment)
        


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    