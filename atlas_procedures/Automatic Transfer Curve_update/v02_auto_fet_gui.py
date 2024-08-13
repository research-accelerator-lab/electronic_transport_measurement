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

from v02_auto_fet_procedure import v02_AutoFETProcedure


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
        boxes = ['atlas_addr', 'study_id', 'wafer_id','map_1_chip_id', 'map_2_chip_id','map_3_chip_id',
                 'V_g_start','V_g_end','V_g_sweep_rate','V_d']
        
        super(MainWindow, self).__init__(
            procedure_class=v02_AutoFETProcedure,
            inputs=boxes,
            displays=boxes,

            x_axis='Gate Voltage (V)',
            y_axis=['Gate Current (A)','Drain Current (A)','abs(Drain Current) (A)'],
            
            sequencer=True,                                      
            sequencer_inputs=['map_id', 'atlas_config', 'device', 'map_config'],
            sequence_file="device_sequence.txt"
        )
        
        self.setWindowTitle('Automated FET')


    def queue(self, procedure=None):
        
        if procedure is None:
            procedure = self.make_procedure()
             
        # Finding Paramteres form Procedure 
        device = str(procedure.device)
        map_id = str(procedure.map_id)
        atlas_config = str(procedure.atlas_config)
        wafer_id = str(procedure.wafer_id)
        study_id = str(procedure.study_id)
        

        # Identifying Chip 
        if map_id == '1':
            chip_id = str(procedure.map_1_chip_id)
        elif map_id == '2':
            chip_id = str(procedure.map_2_chip_id)
        elif map_id == '3':
            chip_id = str(procedure.map_3_chip_id)
            
            
        # Renaming and deciding folderpath to save data
        if atlas_config == "0":
            device = str(int(device)+4)
        
        if study_id=='S1':
            if 9 <= int(chip_id) <= 12:
                subfolder = 'fet_gtlm\\raw_files'
            elif 13 <= int(chip_id) <= 16:
                subfolder = 'fet_square\\raw_files'
            directory = r"Z:\projmon\vdp-fet-board-data\Study 1\\" + study_id + "_" + wafer_id + '\\' + subfolder
        else:
            directory = r"Z:\projmon\vdp-fet-board-data\Study " + study_id[-1] +"\\" + study_id + "_" + wafer_id
        
        prefix = study_id + "_" + wafer_id + "_chip" + chip_id + "_device" + device.zfill(2)
        
        filename = unique_filename(directory, prefix=prefix, suffix="trial", ext='csv', datetimeformat="")
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    
