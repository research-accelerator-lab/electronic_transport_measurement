import pandas as pd
from matplotlib import pyplot as plt
import os
from scipy.stats import linregress as linreg 
from scipy.stats import zscore as zscore
from statistics import mean as statmean
import numpy as np

## ------------------ Data Management ------------------

def retrieve_FET_files(folder_path):
    
    file_names = [x for x in os.listdir(folder_path) if x.endswith(".csv")]
    
    file_paths = []
    sample_id = []
    chip_id = []
    device_id = []
    trial_id = []

    for z in range(len(file_names)):
        file_paths.append(os.path.join(folder_path,file_names[z]))
        sample_id.append(file_names[z][:-4])
        chip_id.append(sample_id[z].split('_')[2][-2:])
        device_id.append(sample_id[z].split('_')[3][-2:])
        trial_id.append(sample_id[z].split('_')[4][-2:])

    return file_paths, sample_id, chip_id, device_id, trial_id


def read_FET_data(file_path, clean='Yes'):
    
    data = pd.read_csv(file_path,usecols=[1,2,3],skiprows=18)
    
    if clean=='Yes':
        data = clean_FET_data(data)
    V_g = data['Gate Voltage (V)']
    I_g = data['Gate Current (A)']
    I_d = data['Drain Current (A)']
    V_d = float(pd.read_csv(file_path,usecols=[0],skiprows=2,nrows=1, header=None)[0][0][-5:-2])
    sweep_rate = float(pd.read_csv(file_path,usecols=[0],skiprows=6,nrows=1, header=None)[0][0][-6:-4]) 
    
    return V_g, I_g, I_d, V_d, sweep_rate


def clean_FET_data(data): # eliminate outlier datapoints 
    z_score_threshold = 3 # can change this threshold
    
    z_scores = np.abs(zscore(data))
    data_clean = data[(z_scores<z_score_threshold).all(axis=1)]
    data_clean = data_clean.reset_index(inplace = False)
    
    return data_clean


def find_FET_file(subfolder_path, chip, device, trial):
    
    wafer_ID = subfolder_path.split(os.sep)[-2]
    file_name = wafer_ID + '_chip' + str(chip).zfill(2) + '_device' + str(device).zfill(2) + '_trial' + str(trial).zfill(2)
    file_path = os.path.join(subfolder_path+'\\raw_files', file_name + '.csv')
    
    return file_path

## ------------------ FET Analysis & Plotting ------------------

def FET_analysis(V_g, I_g, I_d, V_d, diel_material, diel_thickness, aspect_ratio):
    
    # Dielectric properties
    if diel_material == 'SiO2':
        diel_k = 3.2
    elif diel_material == 'HfO2':
        diel_k = 25
    diel_C = diel_k*8.85E-12/(diel_thickness/1E9)  # specific capacitance of dielectric (F/m2)
    
    
    # Check data is enough and device didn't break down
    if len(V_g) > 200 and I_g.max() <= 1E-6: # enough data and no breakdown
        
        # Find range of Vg values for linear fit 
        V_g_index = [i for i in range(len(V_g)) if V_g[i]==100]
        V_g_fit = V_g[V_g_index[0]:V_g_index[1]]
        I_d_fit = I_d[V_g_index[0]:V_g_index[1]]
        V_g_fit, I_d_fit = zip(*sorted(zip(V_g_fit, I_d_fit)))
        

        # Linear fit of Id vs Vg
        slope, intercept, r_sq_value, p_value, std_err = linreg(V_g_fit, I_d_fit) 
        trendline = [slope, intercept]
    
        if r_sq_value > 0.3: # checking quality of the fit, at least something that makes sense
            
            # Solving for FET parameters
            V_th = round(-intercept/slope,1)
            mobility = round(slope*aspect_ratio*1E4/(diel_C * V_d),3)  # mobility [=] cm^2/V-s
            R_sq = round(r_sq_value,3)

            #I_off_array = [abs(I_d[i]) for i in range(len(V_g)) if V_g[i]<0] #(V_th*0.5)
            if V_g.iloc[0]==V_g.iloc[-1]-1: # complete scan
                I_off_array = I_d[1:20].tolist()+I_d[-20:-1].tolist() # first twenty points
            else:
                I_off_array = I_d[1:20]
            I_off_array = [abs(I) for I in I_off_array]
            I_off = abs(statmean(I_off_array))
            I_on_off_ratio = abs(round(max(I_d)/I_off,0))
           
            
            I_off = abs(statmean(I_off_array))
            I_on_off_ratio = abs(round(max(I_d)/I_off,0))
           
        else:
            V_th, I_on_off_ratio, mobility, R_sq, trendline, I_off = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
            
    else:
        V_th, I_on_off_ratio, mobility, R_sq, trendline, I_off = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]    

    return V_th, I_on_off_ratio, mobility, R_sq, trendline, I_off

    
def plot_FET_format(sample_name):
    
    # Setting up the plots
    fig, axes = plt.subplots(1,3, figsize=(13.5, 4), sharex=True)
    plt.rcParams.update({'font.size': 10})
    plt.suptitle(str(sample_name))
    axes[2].set_yscale('log')
    
    # Changing plot display
    axes[0].set_ylabel('$\mathregular{I_{g}}$ (A)')
    axes[0].set_xlabel('$\mathregular{V_{g}}$ (V)')
    axes[1].set_ylabel('$\mathregular{I_{d}}$ (A)')
    axes[1].set_xlabel('$\mathregular{V_{g}}$ (V)')
    axes[2].set_ylabel('log($\mathregular{|I_{d}| (A)}$)')
    axes[2].set_xlabel('$\mathregular{V_{g}}$ (V)')

    return fig, axes


def plot_FET(sample_name, V_g, I_g, I_d):
    
    fig, axes = plot_FET_format(sample_name)
    
    if len(V_g) > 0:
        
        # Index where reverse scan starts
        index_switch = V_g.argmax() + 1
        
        # Plotting Ig vs Vg
        axes[0].plot(V_g[:index_switch],I_g[:index_switch],label='$\mathregular{I_{g}}$'+r'$\rightarrow$',color="black",marker='None',linestyle='solid') 
        axes[0].plot(V_g[index_switch+1:],I_g[index_switch+1:],label='$\mathregular{I_{g}}$'+r'$\leftarrow$',color="black",marker='None',linestyle='dashed')
        
        # Plotting Id vs Vg
        axes[1].plot(V_g[:index_switch],I_d[:index_switch],label='$\mathregular{I_{d}}$'+r'$\rightarrow$',color="blue",marker='None',linestyle='solid') 
        axes[1].plot(V_g[index_switch+1:],I_d[index_switch+1:],label='$\mathregular{I_{d}}$'+r'$\leftarrow$',color="blue",marker='None',linestyle='dashed') 
        
        # Plotting log(Id) vs Vg
        axes[2].plot(V_g[:index_switch],abs(I_d[:index_switch]),label='|$\mathregular{I_{d}}$|'+r'$\rightarrow$',color="blue",marker='None',linestyle='solid') 
        axes[2].plot(V_g[index_switch+1:],abs(I_d[index_switch+1:]),label='|$\mathregular{I_{d}}$|'+r'$\leftarrow$',color="blue",marker='None',linestyle='dashed') 
    
        # Adding legend
        axes[0].legend(fontsize='small',loc='lower left')
        axes[1].legend(fontsize='small',loc='lower left')
        axes[2].legend(fontsize='small',loc='lower left')
    
    return fig, axes


def plot_FET_analysis(sample_name, V_g, I_g, I_d, V_d, sweep_rate, parameters):


    # Setting up subplots
    fig, axes = plot_FET(sample_name, V_g, I_g, I_d)

    # Unzipping parameters
    V_th, I_on_off_ratio, mobility, R_sq, trendline, I_off = parameters 
    
    # Plotting linear fit line
    slope, intercept = trendline
    x_values = [V_th, max(V_g)]
    y_values = [slope * x + intercept for x in x_values]
    axes[1].plot(x_values, y_values, label='fit', color='black', linestyle='dotted')
             
    # Plotting I_off line
    axes[2].plot([V_g[0],V_g[20]], [I_off,I_off],label='I$_{{{off}}}$', color='black', linestyle='dotted')
                  
    # Label plots with parameters of interest
    axes[1].text(0.05, 0.98, " V$_T$ = " + str(V_th) + 'V', transform=axes[1].transAxes, fontsize="small", verticalalignment='top')
    axes[1].text(0.05, 0.91, " $\mu$$_{{{FE}}}$ = " + str(mobility) + " cm$^2$/V/s", transform=axes[1].transAxes, fontsize="small", verticalalignment='top')
    axes[1].text(0.05, 0.83, " R$^2$ = " + str(R_sq), transform=axes[1].transAxes, fontsize="small", verticalalignment='top')
    axes[2].text(0.05, 0.98, " I$_{{{on/off}}}$ = " + "{:.1e}".format(I_on_off_ratio), transform=axes[2].transAxes, fontsize="small", verticalalignment='top')
    axes[2].text(0.05, 0.91, " V$_g$ Sweep = " + str(sweep_rate) + 'V/s', transform=axes[2].transAxes, fontsize="small", verticalalignment='top')
    axes[2].text(0.05, 0.83, " V$_d$ = " + str(V_d) + 'V', transform=axes[2].transAxes, fontsize="small", verticalalignment='top')
    
    # Updating legend
    axes[1].legend(fontsize='small',loc='lower left')
    axes[2].legend(fontsize='small',loc='lower right')

    return fig, axes