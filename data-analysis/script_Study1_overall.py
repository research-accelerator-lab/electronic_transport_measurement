import pandas as pd
from matplotlib import pyplot as plt
import os
import numpy as np
import matplotlib.colors
import colorsys

#---------------------------------------------------------

# Indentifying the correct folder:
S1_folder = r'C:\Users\amber\Desktop\Study 1'
S1_folder_paths = [f.path for f in os.scandir(S1_folder) if f.is_dir()]

# Grab metadata for the following:
diel_material = 'SiO2'
diel_thickness = 300 # nm
sc_thickness = [3.5,5,10,20,40] #nm

# Dielectric properties
if diel_material == 'SiO2':
    diel_k = 3.2
elif diel_material == 'HfO2':
    diel_k = 25
diel_C = diel_k*8.85E-12/(diel_thickness/1E9)  # specific capacitance of dielectric (F/m2)


#----------------------------------- COMPARING RESULTS ACROSS STUDY 1 FOLDERS ------------------------------------------------------------------------------
        
# S1_folder     
wafer_groups = [['06A','05C','07A','08A','06C']]   
labels = ['3.5 nm','5 nm','10 nm','20 nm','40 nm']

for z in range(len(wafer_groups)):
    
    wafer_ids = wafer_groups[z]
    
    
    ## ---- FET
    fet_L = []
    fet_Vth_mean, fet_Vth_std = [[],[]]
    fet_mobility_mean, fet_mobility_std = [[],[]]
    fet_Ionoff_mean, fet_Ionoff_std = [[],[]]
    
    # Setting up the plot 
    fig, axes = plt.subplots(1,3, figsize=(13, 4), sharex=True)
    plt.rcParams.update({'font.size': 10})
    plt.suptitle('Overall FET Analysis')
    axes[2].set_yscale('log')
    
    # Changing axis labels
    axes[0].set_ylabel('$\mathregular{V_{th}}$ (V)')
    axes[1].set_ylabel('$\mu$$_{{{FE}}}$ (cm$^2$/V/s)')
    axes[2].set_ylabel('I$_{{{on/off}}}$')
    for x in range(len(axes)):
        axes[x].set_xlabel('L (mm)') 
        
    # Making color ranges to plot with
    r,g,b = matplotlib.colors.ColorConverter.to_rgb('darkmagenta')
    h,l,s=colorsys.rgb_to_hls(r,g,b) 
    l_varied=list(np.linspace(0.9,0.1,len(labels)))
    label_colors = [colorsys.hls_to_rgb(h,x,s) for x in l_varied]
    
    for q in range(len(wafer_ids)):
        
        subfolder_wafer = S1_folder + '\\S1_'+wafer_ids[q]
        subfolder_fet = subfolder_wafer + '\\fet_square'
        
        
        df_fet = pd.read_csv(subfolder_fet + '\\properties.txt', header=0, skiprows=1, names=['Device #','L (mm)', ('V_th (V)','mean'), ('V_th (V)','std'), 
                            ('mobility (cm2/V/s)','mean'), ('mobility (cm2/V/s)','std'),('I_on/off','mean'), ('I_on/off','std'), 'sample_size'])
        
        fet_L.append(df_fet['L (mm)'].tolist()) 
        fet_Vth_mean.append(df_fet[('V_th (V)','mean')].tolist())
        fet_Vth_std.append(df_fet[('V_th (V)','std')].tolist())
        fet_mobility_mean.append(df_fet[('mobility (cm2/V/s)','mean')].tolist())
        fet_mobility_std.append(df_fet[('mobility (cm2/V/s)','std')].tolist())
        fet_Ionoff_mean.append(df_fet[('I_on/off','mean')].tolist())
        fet_Ionoff_std.append(df_fet[('I_on/off','std')].tolist())
        
        # Plotting the data, with y-axis errorbars
        axes[0].errorbar(fet_L[q],fet_Vth_mean[q], yerr=fet_Vth_std[q], color=label_colors[q], label=labels[q], marker='o',linestyle='solid', capsize = 3) 
        axes[1].errorbar(fet_L[q],fet_mobility_mean[q], yerr=fet_mobility_std[q], color=label_colors[q],label=labels[q], marker='o',linestyle='solid', capsize = 3) 
        axes[2].errorbar(fet_L[q],fet_Ionoff_mean[q], yerr=([0]*df_fet.shape[0],fet_Ionoff_std[q]), color=label_colors[q],label=labels[q], marker='o',linestyle='solid', capsize = 3) 

    axes[0].legend(loc="upper right", fontsize='small')
    plt.tight_layout()
    plt.show()
    
    # Saving the plot and dataframe
    fig.savefig(S1_folder + '\\ZnO_fet.png', dpi=200)
        
       
    ## VDP --------
    
    vdp_L = []
    vdp_Rs = [] 
    vdp_mobility = []
    vdp_carrier = [] 
    
    # Setting up the plots
    fig, axes = plt.subplots(1,3, figsize=(13, 4))
    plt.rcParams.update({'font.size': 10})
    plt.suptitle('VdP Analysis')
    axes[0].set_yscale('log')
    axes[2].set_yscale('log')
    
    # Changing plot display
    axes[0].set_xlabel('$\mathregular{V_{g}}$ (V)')
    axes[0].set_ylabel('$\mathregular{R_{sheet}}$ (Ohm)')
    axes[1].set_xlabel('L (mm)')
    axes[1].set_ylabel('$\mu$$_{{{app}}}$ (cm$^2$/V/s)')
    axes[2].set_xlabel('$\mathregular{V_{g}}$ (V)')
    axes[2].set_ylabel('Carrier Conc. (1/m$^3$)')
    
    
    # Making color ranges to plot with
    r,g,b = matplotlib.colors.ColorConverter.to_rgb('darkred')
    h,l,s=colorsys.rgb_to_hls(r,g,b) 
    l_varied=list(np.linspace(0.1,0.6,len(labels)))
    label_colors = [colorsys.hls_to_rgb(h,x,s) for x in l_varied]

    for q in range(len(wafer_ids)):
        
        subfolder_wafer = S1_folder + '\\S1_'+wafer_ids[q]
        subfolder_vdp = subfolder_wafer + '\\vdp'
        
        df_vdp1 = pd.read_csv(subfolder_vdp + '\\R_sheet.txt', header=0, skiprows=1, names=['L (mm)', ('Rs@60V','mean'), ('Rs@60V','std'), 
                            ('Rs@80V','mean'), ('Rs@80V','std'),('Rs@100V','mean'), ('Rs@100V','std'),('Rs@120V','mean'), ('Rs@120V','std'), 'sample_size'])
        df_vdp2 = pd.read_csv(subfolder_vdp + '\\properties.txt', header=0, names = ['L (mm)', 
                            'mobility_app (cm2/V/s)', 'carriers@60V', 'carriers@80V','carriers@100V', 'carriers@120V'])
        
        R = [] # @ 60, 80, 100, 120V
        carrier = [] 
        for i in range(4):
            R.append(df_vdp1.iloc[1,1+2*i])
            carrier.append(df_vdp2.iloc[1,2+i])
        
        vdp_L.append(df_vdp1['L (mm)'].tolist())
        vdp_Rs.append(R)
        vdp_carrier.append(carrier)
        vdp_mobility.append(df_vdp2['mobility_app (cm2/V/s)'].tolist())
        Vg=[60,80,100,120]
    
        axes[0].plot(Vg, vdp_Rs[q], color=label_colors[q], label=labels[q], marker='o',linestyle='solid')
        axes[1].plot(vdp_L[q], vdp_mobility[q], color=label_colors[q], label=labels[q], marker='o',linestyle='solid')
        axes[2].plot(Vg, vdp_carrier[q], color=label_colors[q], label=labels[q], marker='o',linestyle='solid')
        
        
    axes[0].legend(loc="upper right", fontsize='small')
    
    # Setting axis limits
    if diel_material == 'SiO2' and diel_thickness == 300:
        axes[1].set_ylim([0,13])
        
    plt.tight_layout()
    plt.show()
    
    # Saving the plot and dataframe
    fig.savefig(S1_folder + '\\ZnO_vdp.png', dpi=200)  
    
    
    
    
    
    
    
    
    
    
    
    
    
