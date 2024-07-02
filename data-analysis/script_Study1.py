from functions_FET import retrieve_FET_files, read_FET_data, find_FET_file, FET_analysis, plot_FET_format, plot_FET, plot_FET_analysis
from functions_VdP import retrieve_VdP_files, read_VdP_data, VdP_analysis, plot_VdP, plot_VdP_analysis
import pandas as pd
from matplotlib import pyplot as plt
import dataframe_image as dfi
import math
import os
import numpy as np
from scipy.stats import zscore as zscore
from scipy.stats import linregress as linreg 
import matplotlib.colors
import colorsys
from matplotlib.ticker import FormatStrFormatter

#---------------------------------------------------------

# Indentifying the correct folder:
S1_folder = r'C:\Users\amber\Desktop\Study 1'
S1_folder_paths = [f.path for f in os.scandir(S1_folder) if f.is_dir()]

# Grab metadata for the following:
diel_material = 'SiO2'
diel_thickness = 300 # nm
sc_thickness = [5,10,20] #nm

# Dielectric properties
if diel_material == 'SiO2':
    diel_k = 3.2
elif diel_material == 'HfO2':
    diel_k = 25
diel_C = diel_k*8.85E-12/(diel_thickness/1E9)  # specific capacitance of dielectric (F/m2)

#----------------------------------- ANALYSIS PER EVERY STUDY 1 FOLDER PATH ------------------------------------------------------------------------------

for p in range(len(S1_folder_paths)):
    
    ## ------------------ GENERAL FET (2-probe) ANALYSIS  ------------------
    
    # Identifying subfolders:
    subfolder_paths = [S1_folder_paths[p] + '\\fet_gtlm', S1_folder_paths[p] + '\\fet_square']
    
    
    # Analyzing and Creating a Plot for Each FET  ---------------------------------
    for s in range(len(subfolder_paths)):
        
        if os.listdir(subfolder_paths[s]+'\\raw_files') != []: # confirming folder is not empty
        
            # Finding all .csv files in the folder
            file_paths, sample_id, chip_id, device_id, trial_id = retrieve_FET_files(subfolder_paths[s]+'\\raw_files')  
            
            
            # Physical parameters for each subfolder, defined by the pattern:
            if s == 0: # fet_gtlm folder
                channel_lengths = [1, 1, 1, 1, 1, 1/2, 2, 3] # [mm]
                channel_widths = [1, 2, 3, 4, 1/2, 1, 1, 1] # [mm]
            elif s == 1: # fet_square folder
                channel_lengths = [0.05, 0.15, 0.3, 0.5, 1, 1.5, 2, 3] # [mm]
                channel_widths = [0.05, 0.15, 0.3, 0.5, 1, 1.5, 2, 3] # [mm]
                
                
            # Initializing data storage
            compiled_data = []
            
            # FET plot and analysis for each sample -------------
            
            for z in range(len(sample_id)):
                
                # Performing analysis & plotting if it hasn't already been done
                if os.path.exists(subfolder_paths[s] + '\\raw_files\\' + str(sample_id[z]) +'_fit.txt') == False:
                        
                    # Finding the dimensions of that device
                    device_index = int(device_id[z])-1
                    L = channel_lengths[device_index]
                    W = channel_widths[device_index]
                    aspect_ratio = L/W
                    
                    # Extracting data from file
                    V_g, I_g, I_d, V_d, sweep_rate = read_FET_data(file_paths[z], clean='Yes')
                    
                    # Solving for FET parameters
                    V_th, I_on_off_ratio, mobility, R_sq, trendline, I_off = FET_analysis(V_g, I_g, I_d, V_d, diel_material, diel_thickness, aspect_ratio)
                
                    # Plotting the data 
                    if math.isnan(R_sq): # for samples with failed analysis
                        fig, axes = plot_FET(sample_id[z], V_g, I_g, I_d)
                    else:
                        parameters = [V_th, I_on_off_ratio, mobility, R_sq, trendline, I_off]
                        fig, axes = plot_FET_analysis(sample_id[z], V_g, I_g, I_d, V_d, sweep_rate, parameters)
                    
                    plt.tight_layout()
                    plt.show()
                    fig.savefig(subfolder_paths[s] + '\\raw_files\\' + str(sample_id[z]) +'_figure.png',dpi=200)
                      
                    # Writing a text file with the data
                    with open(subfolder_paths[s] + '\\raw_files\\' + str(sample_id[z]) +'_fit.txt', 'w') as f:
                        f.write('Chip #,Device #,Trial #,L (mm),W (mm),L/W,V_th (V),mobility (cm2/V/s),I_on/off,R_sq')
                        f.write('\n')
                        f.write(str(chip_id[z]) +','+ str(device_id[z]) +','+ str(trial_id[z]) +','+ str(L) +','+ str(W) +','+ str(aspect_ratio) +','+
                                str(V_th) +','+ str(mobility) +','+ str(I_on_off_ratio) +','+ str(R_sq))
                    
                compiled_data.append(np.loadtxt(subfolder_paths[s] + '\\raw_files\\' + str(sample_id[z]) +'_fit.txt', skiprows=1, delimiter=',', dtype="str").tolist())
            
            # Creating compiled dataframe:
            df = pd.DataFrame(compiled_data, columns=['Chip #','Device #','Trial #','L (mm)','W (mm)','L/W','V_th (V)','mobility (cm2/V/s)','I_on/off','R_sq'])   
                
            # Delete rows with nan
            df = df.apply(pd.to_numeric, errors = 'coerce')
            df = df.dropna() 
            
            # Find the best performing run (highest I_on/off) for each chip and device (minimize duplicate trials):
            df = df.sort_values('I_on/off', ascending=False).drop_duplicates(["Chip #","Device #"])
            df = df.sort_values(by=['Chip #','Device #'])
            df = df.reset_index(drop = True)
            
            # Saving compiled data -------------
            
            df.to_csv(subfolder_paths[s] + '\\raw_files\\compiled_data.txt', index=False)
            dfi.export(df, subfolder_paths[s] + '\\raw_files\\compiled_data.png', table_conversion = 'matplotlib')
        
        
    ## ------------------ COMPARING BEST FETs and AVERAGE FET PROPERTIES  ------------------
    
    for s in range(len(subfolder_paths)):
        
        if os.path.exists(subfolder_paths[s] + '\\raw_files\\compiled_data.txt') == True: # conduct analysis if file exists
        
            # Calling data
            df = pd.read_csv(subfolder_paths[s] + '\\raw_files\\compiled_data.txt')
            
            if df.shape[0] > 0: # if the dataframe is NOT empty
                
                # Drop devices 2,3,4,5 for gtlm study bc they have a different channel width 
                if s == 0: # gtlm_folder
                    if 2 in df['Device #'].tolist():
                        df = df[(df['Device #'] != 2)]
                    if 3 in df['Device #'].tolist():
                        df = df[(df['Device #'] != 3)]
                    if 4 in df['Device #'].tolist():
                        df = df[(df['Device #'] != 4)]
                    if 5 in df['Device #'].tolist():
                        df = df[(df['Device #'] != 5)]
                      
                # Cleaning the data for outliers  
                z_scores = df[['V_th (V)','mobility (cm2/V/s)','I_on/off']].apply(zscore)
                for i in range(z_scores.shape[0]):
                    drop = False
                    for j in range(z_scores.shape[1]):
                        if abs(z_scores.iloc[i,j]) > 3:
                            drop = True
                    if drop == True:
                        df = df.drop(index=[i])
                df = df.reset_index(drop=True)
                    
            
                # OVERALL PLOT #1: Properties vs. L  --------------------
            
                # Calculating the average & standard deviation by each device
                df_stats = df.groupby('Device #', as_index=False)['V_th (V)','mobility (cm2/V/s)','I_on/off'].agg(['mean','std'])
                df_stats['sample_size'] = df.groupby('Device #')['Device #'].count()  # tracking the number devices sampled
                df_stats = df_stats.reset_index()
                df_stats = df_stats.replace(math.nan,0) # if std is NaN, replace with 0
                
                # Setting up the plot 
                fig, axes = plt.subplots(1,3, figsize=(13, 4), sharex=True)
                plt.rcParams.update({'font.size': 10})
                axes[2].set_yscale('log')
                
                # Changing axis labels
                axes[0].set_ylabel('$\mathregular{V_{th}}$ (V)')
                axes[1].set_ylabel('$\mu$$_{{{FE}}}$ (cm$^2$/V/s)')
                axes[2].set_ylabel('I$_{{{on/off}}}$')
                for x in range(len(axes)):
                    axes[x].set_xlabel('L (mm)') 
                    
                # Setting axis limits
                if diel_material == 'SiO2' and diel_thickness == 300:
                    axes[0].set_ylim([60,100])
                    axes[1].set_ylim([0,20])
                    axes[2].set_ylim([1E0,1E5])
                    
                    #df_stats[('V_th (V)','mean')].max()
                
                # Physical parameters from pattern and plot properties
                if s == 0: # fet_gtlm folder
                    plt.suptitle('Varying Channel Length, W = 1 mm')
                    channel_lengths = [1, 1, 1, 1, 1, 1/2, 2, 3] # [mm]
                    if df_stats['Device #'][0] == 1 and df_stats['Device #'][1] == 6: # if data for device 1 and 6 is present
                        df_stats = df_stats.rename({0:1,1:0}).sort_index() # reorder df_stats so it is in order of L
                elif s == 1: # fet_square folder
                    plt.suptitle('Varying Square Channel Size')
                    channel_lengths = [0.05, 0.15, 0.3, 0.5, 1, 1.5, 2, 3] # [mm]
                
                # Finding the channel lengths for each device
                L = []
                num_devices=df_stats.shape[0]
                for x in range(num_devices):
                    device_id = df_stats['Device #'][x]
                    device_index = int(device_id)-1
                    L.append(channel_lengths[device_index])
                df_stats.insert(loc=1, column='L (mm)', value=L)
            
            
                # Plotting the data, with y-axis errorbars
                axes[0].errorbar(L,df_stats[('V_th (V)','mean')].tolist(), yerr=df_stats[('V_th (V)','std')].tolist(), color="black",marker='o',linestyle='solid', capsize = 3) 
                axes[1].errorbar(L,df_stats[('mobility (cm2/V/s)','mean')].tolist(), yerr=df_stats[('mobility (cm2/V/s)','std')].tolist(), color="black",marker='o',linestyle='solid', capsize = 3) 
                axes[2].errorbar(L,df_stats[('I_on/off','mean')].tolist(), yerr=([0]*df_stats.shape[0],df_stats[('I_on/off','std')].tolist()), color="black",marker='o',linestyle='solid', capsize = 3) 
            
                plt.tight_layout()
                plt.show()
                
                # Saving the plot and dataframe
                fig.savefig(subfolder_paths[s] + '\\properties_fig.png', dpi=200)
                df_stats.to_csv(subfolder_paths[s] + '\\properties.txt', index=False)
                dfi.export(df_stats, subfolder_paths[s] + '\\properties.png', table_conversion = 'matplotlib')
                
                    
                # OVERALL PLOT #2: Comparing Best Performing Devices --------------
                     
                # Locating best performing devices
                df_max = df.sort_values('I_on/off', ascending=False).drop_duplicates(["Device #"])
                df_max = df_max.sort_values(by=['L (mm)'])
                df_max = df_max.reset_index(drop = True)
                
                # Setting up the plot
                if s == 0: # fet_gtlm folder
                    plt_suptitle = 'Varying Channel Length, W = 1 mm'
                elif s == 1: # fet_square folder
                    plt_suptitle = 'Varying Square Channel Size'
                label_values = df_max['L (mm)'].tolist()
                labels = ['L (mm) = ' + str(label_values[x]) for x in range(len(label_values))]
                
                fig, axes = plot_FET_format(plt_suptitle)
                
                # Plotting each device
                for z in range(df_max.shape[0]):
                    
                    # Finding the file with the data
                    file_path = find_FET_file(subfolder_paths[s], str(df_max['Chip #'][z]).zfill(2), 
                                          str(df_max['Device #'][z]).zfill(2), str(df_max['Trial #'][z]).zfill(2))
                    
                    # Extracting data from file
                    V_g, I_g, I_d, V_d, sweep_rate = read_FET_data(file_path, clean='Yes')
                    
                    # Plotting data
                    #stop = V_g.argmax() # plotting only forward scan
                    stop = len(V_g) # plotting entire scan
                    axes[0].plot(V_g[0:stop],I_g[0:stop],label=labels[z],marker='None',linestyle='solid') 
                    axes[1].plot(V_g[0:stop],I_d[0:stop],label=labels[z],marker='None',linestyle='solid')  
                    axes[2].plot(V_g[0:stop],abs(I_d[0:stop]),label=labels[z],marker='None',linestyle='solid')
                    
                # Adding legends
                handles, labels = axes[0].get_legend_handles_labels()
                axes[2].legend(handles, labels, fontsize='small', loc='lower right')
                
                plt.tight_layout()
                plt.show()
                
                # Saving the plot and dataframe
                fig.savefig(subfolder_paths[s] + '\\performance_fig.png', dpi=200)
                df_max.to_csv(subfolder_paths[s] + '\\performance.txt', index=False)
                dfi.export(df_max, subfolder_paths[s] + '\\performance.png', table_conversion = 'matplotlib')
                
    
    ## ------------------ GATED TRANSMISSION MODEL ANALYSIS  ------------------
    
    # Identifying subfolder:
    subfolder_path = S1_folder_paths[p] + '\\fet_gtlm'
    
    if os.path.exists(subfolder_path + '\\performance.txt') == True: # conduct analysis if file exists
        
        # Pulling the analyzed data - using the best device file
        df_max = pd.read_csv(subfolder_path + '\\performance.txt')
        
        # Setting expected V_g arrays
        if diel_material == 'SiO2' and diel_thickness == 300:
            V_g_samples = [80,90,100,110,120]
        
        # Solving R_at_Vg (total R) for each V_g ------------------
        
        # Initializing blank array
        R_at_Vg = []
        for i in range(len(V_g_samples)): # for number of V_g's
            R_at_Vg.append([])
            for z in range(df_max.shape[0]):
                R_at_Vg[i].append([])
        
        # Calculating R_at_Vg
        for z in range(df_max.shape[0]): # for number of devices
             
             # Finding the file with the data
             file_path = find_FET_file(subfolder_path, df_max['Chip #'][z], df_max['Device #'][z], df_max['Trial #'][z])
             
             # Extracting data from file
             V_g, I_g, I_d, V_d, sweep_rate = read_FET_data(file_path, clean='Yes')
             V_th = df_max['V_th (V)'][z]
             
             # Calculating resistances at a specific V_g
             R_tot = []
             for i in range(len(V_g_samples)):
                 V_g_idx = [j for j in range(len(V_g)) if V_g[j]==V_g_samples[i]]
                 if len(V_g_idx) == 0: 
                     R_at_Vg[i][z] = math.nan
                 elif len(V_g_idx) > 0:
                     R_at_Vg[i][z] = V_d/I_d[V_g_idx[0]]
                     
        # Plotting ----------------
        
        # Setting up the plots
        fig, axes = plt.subplots(1,2, figsize=(9, 4))
        plt.rcParams.update({'font.size': 10})
        plt.suptitle('Gated Transfer Length Method')
        #axes[0].set_yscale('log')
        axes[1].set_yscale('log')
        
        # Changing plot display
        axes[0].set_ylabel('$\mathregular{R_{tot}}$ * W (Ohms*mm)')
        axes[0].set_xlabel('L (mm)')
        axes[1].set_ylabel('$\mathregular{R_{contact}}$ (Ohms)')
        axes[1].set_xlabel('$\mathregular{V_{g}}$ (V)')
        
        
        # Solving & plotting contract resistance ------------
        
        R_contact = [] # initializing array
        
        # Calculating & plotting
        for z in range(len(V_g_samples)): # for number of devices
            
            # Calculating R_tot/W for each V_g
            W = 1 #mm
            RW_at_Vg = [R_at_Vg[z][i]*W for i in range(df_max.shape[0])]
            slope, intercept, r_sq_value, p_value, std_err = linreg(df_max['L (mm)'].tolist(), RW_at_Vg) 
            R_contact.append(abs(intercept/W))
            
            # Plotting a new line for each V_g
            label = '$\mathregular{V_{g}}$ = ' + str(V_g_samples[z])+' (V)'
            axes[0].plot(df_max['L (mm)'].tolist(), RW_at_Vg, label=label, marker='o', linestyle='solid') 
            axes[0].plot([0, 3], [intercept, 3*slope], color='black', linestyle = 'dashed') #max L = 3mm
        
        
        # Plotting R_cont vs. V_g
        axes[1].plot(V_g_samples,R_contact,color="black",marker='o',linestyle='solid') 
        
        # Adding legends
        handles, labels = axes[0].get_legend_handles_labels()
        axes[0].legend(handles, labels, fontsize='small', loc='upper left')
        
        plt.tight_layout()
        plt.show()
            
        fig.savefig(subfolder_path + '\\gtlm.png',dpi=200)
                
        # Saving analyzed data in a text file
        with open(subfolder_path + '\\gtlm.txt', 'w') as f:
            f.write('V_g (V),R_contact (Ohm)')
            for i in range(len(V_g_samples)):
                f.write('\n')
                f.write(str(V_g_samples[i]) +','+ str(R_contact[i]))
                
                
    ## ------------------------------------- VAN DER PAUW ANALYSIS  ----------------------------------------

    # Identifying subfolders:
    subfolder_path = S1_folder_paths[p] + '\\vdp'
    
    
    # ----------- Individual VdP Analysis w/ Config Compilation  ---------------------------------

    if os.listdir(subfolder_path + '\\raw_files') != []: # confirming folder is not empty
    
        # Finding all .csv files in the folder
        file_paths, sample_id, chip_id, device_id, config_id, trial_id = retrieve_VdP_files(subfolder_path + '\\raw_files')  
        
        # Physical parameters, defined by the pattern:
        channel_lengths = [0.05, 0.15, 0.3, 0.5, 1, 1.5, 2, 3] # [mm]
        aspect_ratio = 1
        
        # Initializing data storage
        compiled_data = []
        
        for z in range(len(sample_id)):
            
            # Performing analysis & plotting if it hasn't already been done
            if os.path.exists(subfolder_path + '\\raw_files\\' + str(sample_id[z]) +'_data.txt') == False:
                    
                # Finding the dimensions of that device
                if int(chip_id[z]) <= 4: # smaller set of vdp devices
                    device_index = int(device_id[z])-1
                elif int(chip_id[z]) > 4: # larger set of vdp devices
                    device_index = int(device_id[z])+4-1
                L = channel_lengths[device_index]
                
                # Extracting data from file
                time, V_g, I_g, V_vdp, I_vdp, R_channel = read_VdP_data(file_paths[z])
                
                # Analyze data from file
                V_g_values, I_vdp_values, R_at_Vg, I, R_at_I = VdP_analysis(V_g, I_vdp, R_channel)
                
                if len(V_g) > 0: # not an empty file
                
                    # Plotting raw data
                    fig, axes = plot_VdP(sample_id[z], time, V_g, I_g, V_vdp, I_vdp, R_channel)
                    plt.tight_layout()
                    plt.show()
                    fig.savefig(subfolder_path + '\\raw_files\\' + str(sample_id[z]) +'_raw.png',dpi=200)
                    
                    # Plotting analyzed data
                    parameters = [V_g_values, I_vdp_values, R_at_Vg, I, R_at_I, L]
                    fig, axes = plot_VdP_analysis(sample_id[z], parameters)
                    plt.tight_layout()
                    plt.show()
                    fig.savefig(subfolder_path + '\\raw_files\\' + str(sample_id[z]) +'_analyzed.png',dpi=200) 
                  
                # Writing a text file with the data
                if type(V_g_values) == list: #if V_g is a number list, save as string with '_' delimination
                    V_g_values='_'.join(map(str, V_g_values))
                    R_at_I='_'.join(map(str, R_at_I))
                
                with open(subfolder_path + '\\raw_files\\' + str(sample_id[z]) +'_data.txt', 'w') as f:
                    f.write('Chip #,Device #,Config #,Trial #,L (mm),V_g (V),R_channel (Ohm)')
                    f.write('\n')
                    f.write(str(chip_id[z]) +','+ str(device_id[z]) +','+ str(config_id[z]) +','+ str(trial_id[z]) +','+ 
                            str(L) +','+ str(V_g_values) +','+ str(R_at_I))
                
            compiled_data.append(np.loadtxt(subfolder_path + '\\raw_files\\' + str(sample_id[z]) +'_data.txt', skiprows=1, delimiter=',', dtype="str").tolist())
        
        # Creating compiled dataframe
        df = pd.DataFrame(compiled_data, columns=['Chip #','Device #','Config #','Trial #','L (mm)','V_g (V)','R_channel (Ohm)']) 
        
        # Deliminating strings and deleting rows with nan
        for q in range(df.shape[0]):
            if df['V_g (V)'][q]=='nan':
                df=df.drop(q)
            else:
                V = df['V_g (V)'][q].split('_')
                V = [float(V[i]) for i in range(len(V))]
                df['V_g (V)'][q] = V
                R = df['R_channel (Ohm)'][q].split('_')
                R = [float(R[i]) for i in range(len(R))]
                df['R_channel (Ohm)'][q] = R
        df = df.reset_index(drop = True)
        
        # Removing duplicates, based largest change of R
        trial_nums = df.groupby(["Chip #","Device #","Config #"]).count()
        for q in range(trial_nums.shape[0]):
            # locate files with more than 1 datafile for a given chip, device, config
            if trial_nums['Trial #'][q] > 1: 
                chip = trial_nums.index[q][0]
                device = trial_nums.index[q][1]
                config = trial_nums.index[q][2]
                df_duplicate = df[(df['Chip #'] == chip) & (df['Device #'] == device) & (df['Config #'] == config)]
                # for all of the duplicate files found, compare the change in R
                R_change = []
                for v in df_duplicate.index: 
                    R = df_duplicate['R_channel (Ohm)'][v]
                    R_change.append(max(R)/min(R))
                keep_idx = np.argmax(R_change)
                for v in df_duplicate.index: 
                    if v != keep_idx:
                        df=df.drop(v)
        df = df.reset_index(drop = True)
        
        # Saving compiled data -------------
        
        df.to_csv(subfolder_path + '\\raw_files\\compiled_data.txt', index=False)
        dfi.export(df, subfolder_path + '\\raw_files\\compiled_data.png', table_conversion = 'matplotlib', max_rows = 35)

   
        # --------  Compiling Configurations for Each VdP Run  ---------------------------------

        # Identifying wafer for file naming
        wafer_id = subfolder_path.split('\\')[-2]
        
        # Initiatizing array
        compiled_config_data = []
        
        if df.shape[0] > 0: # if the dataframe is NOT empty
            
            # Setting expected V_g array
            if diel_material == 'SiO2' and diel_thickness == 300:
                V_g_sample = [60, 80, 100, 120]
                
            # Deleting data that doesn't match the expected V_g array
            for i in range(df.shape[0]):
                if df['V_g (V)'][i] != V_g_sample:
                    df = df.drop(i)
            df = df.reset_index(drop = True)
        
            # Making string header for text file & df, based on V_g array
            txt_string = ''
            df_string = []
            for V in V_g_sample:
                txt_string += 'R_s(Ohm)@' + str(int(V)) + 'V'
                df_string.append('R_s(Ohm)@' + str(int(V)) + 'V')
                if V != V_g_sample[-1]: # if it's not the last one
                    txt_string += ','
                    
            # Storing list of chips and devices
            chips = [i for i in set(df['Chip #'])]
            chips.sort()
            devices = [i for i in set(df['Device #'])]
            devices.sort()
                                
            # For each chip & device, find the different configs represented
            for chip in chips:
                for device in devices:
                    df_temp = df[(df['Chip #']==chip) & (df['Device #']==device)]
                
                    if df_temp.shape[0] > 0: # if it's not empty
                        index = df_temp.index.tolist() # indexes represented
                        
                        # Setting up the plots
                        fig, axes = plt.subplots(1,2, figsize=(9, 4))
                        plt.rcParams.update({'font.size': 10})
                        plt.suptitle('chip'+chip+'_device'+device)
                        axes[0].set_yscale('log')
                        axes[1].set_yscale('log')
                        
                        # Changing plot display
                        axes[0].set_xlabel('$\mathregular{V_{g}}$ (V)')
                        axes[0].set_ylabel('Resistance (Ohm)')
                        axes[1].set_xlabel('$\mathregular{V_{g}}$ (V)')
                        axes[1].set_ylabel('$\mathregular{R_{sheet}}$ (Ohm)')
                        
                        # Plotting data
                        for i in index:
                            axes[0].plot(df_temp['V_g (V)'][i], df_temp['R_channel (Ohm)'][i], label='config ' + df_temp['Config #'][i], marker='o', linestyle='solid')
                        axes[0].legend(fontsize='small',loc='upper right')
                        
                        
                        # Finding # of configurations
                        configs = df_temp['Config #'].tolist()
                        for i in configs:
                            
                            # Setting defaults
                            config01 = 'no'
                            config02 = 'no'
                            config03 = 'no'
                            config04 = 'no'
                            
                            # Calculating resistances from all the configurations 
                            if '01' in configs and '03' in configs:
                                R_hor1 = df_temp[df_temp['Config #']=='01']['R_channel (Ohm)'].tolist()[0]
                                R_hor2 = df_temp[df_temp['Config #']=='03']['R_channel (Ohm)'].tolist()[0]
                                R_hor = [(R_hor1[j]+R_hor2[j])/2 for j in range(len(R_hor1))]
                                config01, config03 = ['yes','yes']
                            elif '01' in configs:
                                R_hor = df_temp[df_temp['Config #']=='01']['R_channel (Ohm)'].tolist()[0]
                                config01 = 'yes'
                            elif '03' in configs:
                                R_hor = df_temp[df_temp['Config #']=='03']['R_channel (Ohm)'].tolist()[0]
                                config03 = 'yes'
                            if '02' in configs and '04' in configs:
                                R_ver1 = df_temp[df_temp['Config #']=='02']['R_channel (Ohm)'].tolist()[0]
                                R_ver2 = df_temp[df_temp['Config #']=='04']['R_channel (Ohm)'].tolist()[0]
                                R_ver = [(R_ver1[j]+R_ver2[j])/2 for j in range(len(R_ver1))]
                                config02, config04 = ['yes','yes']
                            elif '02' in configs:
                                R_ver = df_temp[df_temp['Config #']=='02']['R_channel (Ohm)'].tolist()[0]
                                config02 = 'yes'
                            elif '04' in configs:
                                R_ver = df_temp[df_temp['Config #']=='04']['R_channel (Ohm)'].tolist()[0]
                                config04 = 'yes'
                            
                            
                        # Calculating average resistance and sheet resistance
                        if 'R_hor' in locals() and 'R_ver' in locals():
                            if len(R_hor) == len(R_ver):
                                R = [(R_hor[k] + R_ver[k])/2 for k in range(len(R_hor))]
                            else: R = R_hor if len(R_hor) > len(R_ver) else R_ver # take the longest
                        elif 'R_hor' in locals():
                            R = R_hor
                        elif 'R_ver' in locals():
                            R = R_ver
                        R_sheet = [(math.pi/math.log(2))*r for r in R]
                            

                        # Plotting R_sheet
                        axes[1].plot(V_g_sample, R_sheet, color='k', marker='o', linestyle='solid')
                        L = df_temp['L (mm)'][index[0]] # all L's should be the same for that device, so use the first
                        axes[1].text(0.98, 0.98, " L = " + str(L) + ' mm', transform=axes[1].transAxes, fontsize="small", verticalalignment='top',horizontalalignment='right')
                   
                        # Saving figure
                        plt.tight_layout()
                        plt.show()
                        fig.savefig(subfolder_path + '\\compiled_configs\\'+wafer_id+'_chip'+chip+'_device'+device+'.png',dpi=200)
                                
                        
                        # Saving analyzed data in a text file
                        with open(subfolder_path + '\\compiled_configs\\'+wafer_id+'_chip'+chip+'_device'+device+'.txt', 'w') as f:
                            f.write('Chip #,Device #,L (mm),config1,config2,config3,config4,'+txt_string)
                            f.write('\n')
                            f.write(chip +','+ device +','+ str(L)+','+ config01+','+ config02 +','+ config03 +','+ config04)
                            for R in R_sheet:
                                f.write(','+ str(R))
            
                        compiled_config_data.append(np.loadtxt(subfolder_path + '\\compiled_configs\\'+wafer_id+'_chip'+chip+'_device'+device+'.txt', skiprows=1, delimiter=',', dtype="str").tolist())
                
                
            # Creating compiled dataframe
            df_compiled = pd.DataFrame(compiled_config_data, columns=(['Chip #','Device #','L (mm)','config1','config2','config3','config4']+df_string)) 
        
            # Saving compiled data
            df_compiled.to_csv(subfolder_path + '\\compiled_configs\\compiled_data.txt', index=False)
            dfi.export(df_compiled, subfolder_path + '\\compiled_configs\\compiled_data.png', table_conversion = 'matplotlib', max_rows = 35)
            
            

    # ----------- Full VdP Analysis Across Devices  ---------------------------------
        
        
    if os.path.exists(subfolder_path + '\\compiled_configs\\compiled_data.txt') == True: # conduct analysis if file exists
        
        # Pulling the analyzed data - using the best device file
        df_compiled = pd.read_csv(subfolder_path + '\\compiled_configs\\compiled_data.txt')
        
        # Cleaning the data for outliers  
        z_scores = df_compiled[df_string].apply(zscore)
        while ((z_scores > 3).any()==True).any() == True:
            for i in range(z_scores.shape[0]):
                drop = False
                for j in range(z_scores.shape[1]):
                    if abs(z_scores.iloc[i,j]) > 3:
                        drop = True
                if drop == True:
                    df_compiled = df_compiled.drop(index=[i])
            df_compiled = df_compiled.reset_index(drop=True)
            z_scores = df_compiled[df_string].apply(zscore)
        
        # Storing list of chips and devices
        df_stats = df_compiled.groupby('L (mm)', as_index=False)[df_string].agg(['mean','std'])
        df_stats['sample_size'] = df_compiled.groupby('L (mm)')['Chip #'].count()  # tracking the number devices sampled
        df_stats = df_stats.reset_index()
        df_stats = df_stats.replace(math.nan,0) # if std is NaN, replace with 0

        # Setting up the plots
        fig, axes = plt.subplots(2,2, figsize=(9, 8))
        plt.rcParams.update({'font.size': 10})
        plt.suptitle(wafer_id + ' VdP Analysis')
        axes[0,0].set_xscale('log')
        axes[0,0].xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        axes[0,0].set_yscale('log')
        axes[0,1].set_yscale('log')
        axes[1,1].set_yscale('log')
        
        # Changing plot display
        axes[0,0].set_xlabel('L (mm)')
        axes[0,0].set_ylabel('$\mathregular{R_{sheet}}$ (Ohm)')
        axes[0,1].set_xlabel('$\mathregular{V_{g}}$ (V)')
        axes[0,1].set_ylabel('$\mathregular{R_{sheet}}$ (Ohm)')
        axes[1,0].set_xlabel('L (mm)')
        axes[1,0].set_ylabel('$\mu$$_{{{app}}}$ (cm$^2$/V/s)')
        axes[1,1].set_xlabel('$\mathregular{V_{g}}$ (V)')
        axes[1,1].set_ylabel('Carrier Conc. (1/cm$^3$)')
        
        # Making color ranges to plot with
        r,g,b = matplotlib.colors.ColorConverter.to_rgb('darkblue')
        h,l,s=colorsys.rgb_to_hls(r,g,b) 
        l_varied=list(np.linspace(0.8,0.1,len(df_string)))
        V_g_colors = [colorsys.hls_to_rgb(h,x,s) for x in l_varied]
          
        # Plotting R_sheet vs. size for all V_g
        for i in range(len(df_string)):
            axes[0,0].errorbar(df_stats['L (mm)'], df_stats[(df_string[i],'mean')].tolist(), yerr=(df_stats[(df_string[i],'std')].tolist()), 
                               label='$\mathregular{V_{g}}$=' + str(int(V_g_sample[i])) +'V', color=V_g_colors[i],marker='o',linestyle='solid', capsize = 3)   
        axes[0,0].legend(fontsize='x-small',loc='upper left')
        
        # Making color ranges to plot with
        r,g,b = matplotlib.colors.ColorConverter.to_rgb('darkgreen')
        h,l,s=colorsys.rgb_to_hls(r,g,b) 
        l_varied=list(np.linspace(0.8,0.2,df_stats.shape[0]))
        L_colors = [colorsys.hls_to_rgb(h,x,s) for x in l_varied]
        
        # Solving for sheet resistance, apparent mobility, charge carrier conc vs. Vg for all sizes
        R_mean = []
        R_std = []
        mobility_app = []
        mobility_app_err = []
        charge_carrier = []
        for i in range(df_stats.shape[0]):
            
            # Sheet conductance
            mean = []
            std = []
            for j in range(len(df_string)):
                mean.append(df_stats[df_string[j],'mean'][i]) 
                if df_stats[df_string[j],'std'][i] == 0: # avoiding division by zero
                    std.append(0)
                else: std.append(df_stats[df_string[j],'std'][i]) 
            R_mean.append(mean)
            R_std.append(std)

            # Apparent mobility
            sheet_cond_mean = [1/R for R in R_mean[i]]
            slope, intercept, r_sq_value, p_value, std_err = linreg(V_g_sample, sheet_cond_mean)  # assuming Vc << Vg-Vt and Vt = constant
            mobility_app.append(slope/(diel_C/10000)) #cm2/V/s
            mobility_app_err.append(std_err/(diel_C/10000)) #cm2/V/s
            
            # Charge carrier conc
            sigma = [num/(sc_thickness[p]/1e7) for num in sheet_cond_mean] # conductivity (S/cm)
            charge_carrier.append([num/(1.60218e-19)/mobility_app[i] for num in sigma]) #1/cm3
            
        # Plotting
        for i in range(df_stats.shape[0]):
            axes[0,1].errorbar(V_g_sample, R_mean[i], yerr = R_std[i], label = 'L='+str(df_stats['L (mm)'][i])+'mm', 
                               color=L_colors[i], marker='o', linestyle='solid', capsize = 3)
            axes[1,1].plot(V_g_sample,charge_carrier[i], label = 'L='+str(df_stats['L (mm)'][i])+'mm', 
                           color=L_colors[i], marker='o', linestyle='solid')
        axes[1,0].errorbar(df_stats['L (mm)'],mobility_app, yerr = mobility_app_err, color='k', marker='o', linestyle='solid')
        
        # Adding legends
        handles, labels = axes[0,1].get_legend_handles_labels()
        axes[0,1].legend(handles[::-1], labels[::-1], loc='upper right', fontsize='x-small') 
        axes[1,1].legend(loc='upper left', fontsize='x-small')
        
        # Setting axis limits
        if diel_material == 'SiO2' and diel_thickness == 300:
            axes[0,1].set_ylim([1E5,1E9])
            axes[1,0].set_ylim([0,20])
            axes[1,1].set_ylim([1E15,1E19])
          
        plt.tight_layout()
        plt.show()
        
        
        # Making string header for df_properties, based on V_g array
        df_carriers_string = ['carriers@'+str(int(V))+'V' for V in V_g_sample]
        
        # Make properties dataframe
        df_properties = pd.DataFrame(charge_carrier, columns=df_carriers_string)
        df_properties.insert(0, 'L (mm)', df_stats['L (mm)'])
        df_properties.insert(1, 'mobility_app (cm2/V/s)', mobility_app)
        df_properties.insert(2, 'mobility_app_err (cm2/V/s)', mobility_app_err)
        
        # Saving the plot and dataframe
        fig.savefig(subfolder_path + '\\analysis.png', dpi=200)
        df_stats.to_csv(subfolder_path + '\\R_sheet.txt', index=False)
        dfi.export(df_stats, subfolder_path + '\\R_sheet.png', table_conversion = 'matplotlib')
        df_properties.to_csv(subfolder_path + '\\properties.txt', index=False)
        dfi.export(df_properties, subfolder_path + '\\properties.png', table_conversion = 'matplotlib')
        

        