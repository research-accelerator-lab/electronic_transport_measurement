# Data-Analysis
Code for rapidly analyzing data generated from running the procedures in the `atlas_procedures` folder.

function_FET holds various function defitions useful for transfer curve analysis
function_VdP holds various function defitions useful for van der Pauw analysis

Script_1 works only if folders are nested as follows:
  Folder
    S1_05C
      fet_gtlm
        raw_files
          [data files]
       fet_square
        raw_files
           [data files]
       vdp
        raw_files
        compiled_configs
           [data files]
    S1_07A
      fet_gtlm
        raw_files
          [data files]
       fet_square
        raw_files
           [data files]
       vdp
        raw_files
        compiled_configs
           [data files]
     S1_08A
      fet_gtlm
        raw_files
          [data files]
       fet_square
        raw_files
           [data files]
       vdp
        raw_files
        compiled_configs
           [data files]
           
 Script 1 contains analysis not included in the paper, such as electron concentration estimations and gated transmission line model analysis.
 
 Script 1 overall includes compiling results into single figures and is to be run after Script 1.
        
    
