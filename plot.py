import sys

from src.config_load import input_data, plots_cfg, default_assumptions
from src.data.data import getFullData
from src.plotting.export_file import exportFigsToFiles
from src.plotting.plot_all import plotAllFigs


# Get list of figs to plot from command line args.
if len(sys.argv) > 1:
    plot_list = sys.argv[1:]
else:
    plot_list = None


# Get plotting data
fullCostData, costData = getFullData(input_data, default_assumptions)


# Run plotting routines to generate figures
figs = plotAllFigs(fullCostData, costData, plots_cfg, plot_list=plot_list)


# Export figures to files
exportFigsToFiles(figs)
