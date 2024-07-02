import pandas as pd
from matplotlib import pyplot as plt
import os
import numpy as np
import matplotlib.colors
import colorsys
import math
from labellines import labelLines

## ------------------ Data Management ------------------

def retrieve_VdP_files(folder_path):
    
    file_names = [x for x in os.listdir(folder_path) if x.endswith(".csv")]
    
    file_paths = []
    sample_id = []
    chip_id = []
    device_id = []
    config_id = []
    trial_id = []

    for z in range(len(file_names)):
        file_paths.append(os.path.join(folder_path,file_names[z]))
        sample_id.append(file_names[z][:-4])
        chip_id.append(sample_id[z].split('_')[2][-2:])
        device_id.append(sample_id[z].split('_')[3][-2:])
        config_id.append(sample_id[z].split('_')[4][-2:])
        trial_id.append(sample_id[z].split('_')[5][-2:])

    return file_paths, sample_id, chip_id, device_id, config_id, trial_id


def read_VdP_data(file_path):
    
    data = pd.read_csv(file_path, skiprows=21)
    
    time = data['timestamp']
    V_g = data['Gate Voltage (V)']
    I_g = data['Gate Current (A)']
    V_vdp = data['VdP Voltage (V)']
    I_vdp = data['VdP Current (A)']
    R_channel = data['Resistance (ohm)']
    
    return time, V_g, I_g, V_vdp, I_vdp, R_channel


def find_VdP_file(subfolder_path, chip, device, config, trial):
    
    wafer_ID = subfolder_path.split(os.sep)[-2]
    file_name = wafer_ID + '_chip' + str(chip).zfill(2) + '_device' + str(device).zfill(2) + '_config' + str(config).zfill(2) + '_trial' + str(trial).zfill(2)
    file_path = os.path.join(subfolder_path+'\\raw_files', file_name + '.csv')
    
    return file_path

## ------------------ VdP Analysis & Plotting ------------------

def plot_VdP(sample_name, time, V_g, I_g, V_vdp, I_vdp, R_channel):
    
    # Setting up the plots
    fig, ax = plt.subplots(1,3, figsize=(13.5, 4))
    axes = np.concatenate([ax, np.array([ax[0].twinx(), ax[1].twinx()])]) # setting up secondary y-axis
    plt.rcParams.update({'font.size': 10})
    plt.suptitle(str(sample_name))
    axes[2].set_yscale('log')
    
    # Changing plot display
    axes[0].set_xlabel('time (s)')
    axes[0].set_ylabel('$\mathregular{V_{g}}$ (V)')
    axes[3].set_ylabel('$\mathregular{I_{g}}$ (A)')
    axes[1].set_xlabel('time (s)')
    axes[1].set_ylabel('$\mathregular{I_{vdp}}$ (A)')
    axes[4].set_ylabel('$\mathregular{V_{vdp}}$ (V)')
    axes[2].set_xlabel('time (s)')
    axes[2].set_ylabel('Resistance (Ohm)')
    axes[3].yaxis.label.set_color('blue')
    axes[4].yaxis.label.set_color('blue')
    axes[3].tick_params(axis='y', colors='blue')
    axes[4].tick_params(axis='y', colors='blue')

    # Plotting data
    axes[0].plot(time, V_g, color='black')
    axes[3].plot(time, I_g, color='blue')
    axes[1].plot(time, I_vdp, color='black')
    axes[4].plot(time, V_vdp, color='blue')
    axes[2].plot(time, R_channel, color='black')

    return fig, axes


def VdP_analysis(V_g, I_vdp, R_channel):
    
    if len(V_g) > 0:
        
        # Only considering forward scan for analysis
        stop = [i for i in range(V_g.shape[0]) if V_g[i]==V_g.max()][-1]+1 # last of max V_g indexes
        V_g_forward = V_g[:stop]
        R_channel_forward = R_channel[:stop]
        
        # Finding unique values of V_g and I_vdp
        V_g_values = [float(i) for i in set(V_g_forward)]
        V_g_values.sort()
        I_vdp_values = [float(i) for i in set(I_vdp)]
        I_vdp_values.sort()
        
        # Separating resistances per gate voltage (forward sweep only)
        R_at_Vg = []
        for i in range(len(V_g_values)):
            R_at_Vg.append([R_channel_forward[j] for j in range(V_g_forward.shape[0]) if V_g[j]==V_g_values[i]])
            
        # Grabbing resistances at middle current
        idx = math.floor(len(I_vdp_values)/2)
        I = I_vdp_values[idx]
        R_at_I = []
        for k in range(len(V_g_values)):
            if len(R_at_Vg[k]) > idx: # if that index exists
                R_at_I.append(R_at_Vg[k][idx])
            else:
                V_g_values.remove(V_g_values[k])
            
    else: 
        V_g_values, I_vdp_values, R_at_Vg, I, R_at_I = [np.nan, np.nan, np.nan, np.nan, np.nan]    
    
    return V_g_values, I_vdp_values, R_at_Vg, I, R_at_I


def plot_VdP_analysis(sample_name, parameters):
    
    # Setting up the plots
    fig, axes = plt.subplots(1,2, figsize=(9, 4))
    plt.rcParams.update({'font.size': 10})
    plt.suptitle(str(sample_name))
    axes[0].set_xscale('log')
    axes[0].set_yscale('log')
    axes[1].set_yscale('log')
    
    # Changing plot display
    axes[0].set_ylabel('Resistance (Ohm)')
    axes[0].set_xlabel('$\mathregular{I_{vdp}}$ (A)')
    axes[1].set_ylabel('Resistance (Ohm)')
    axes[1].set_xlabel('$\mathregular{V_{g}}$ (V)')
    
    # From input variables 
    V_g_values, I_vdp_values, R_at_Vg, I, R_at_I, L = parameters
    
    if type(V_g_values) == list: # V_g_values is not NaN float
            
        # Making color ranges to plot with
        r,g,b = matplotlib.colors.ColorConverter.to_rgb('darkblue')
        h,l,s=colorsys.rgb_to_hls(r,g,b) 
        l_varied=list(np.linspace(0.8,0.1,len(V_g_values)))
        V_g_colors = [colorsys.hls_to_rgb(h,x,s) for x in l_varied]
          
        # Plotting R's per gate voltage as a function of I_vdp 
        for i in range(len(R_at_Vg)):
            num_plots=0
            if len(I_vdp_values)==len(R_at_Vg[i]):
                axes[0].plot(I_vdp_values, R_at_Vg[i], label='$\mathregular{V_{g}}$=' + str(int(V_g_values[i])) + 'V',
                             color=V_g_colors[i],marker='o',linestyle='solid') 
                num_plots+=1
        xvals = [I_vdp_values[0]*1.75 for i in range(num_plots)]
        labelLines(axes[0].get_lines(), xvals=xvals) # labeling each line
        
        # Plotting R at I as a function of gate voltage
        axes[1].plot(V_g_values, R_at_I, color="black", marker='o', linestyle='solid')
        
        # Annotating 
        axes[1].text(0.98, 0.98, " L = " + str(L) + ' mm', transform=axes[1].transAxes, fontsize="small", verticalalignment='top',horizontalalignment='right')
        axes[1].text(0.98, 0.91, " I$_{{vdp}}$ = " + "{:.1e}".format(I) + ' A', transform=axes[1].transAxes, fontsize="small", verticalalignment='top',horizontalalignment='right')
    
    return fig, axes