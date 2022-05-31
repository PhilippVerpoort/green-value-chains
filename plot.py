import sys

from src.load.load_default_data import default_prices, default_options
from src.load.load_config_plot import plots_cfg
from src.data.data import getFullData
from src.plotting.export_file import exportFigsToFiles
from src.plotting.plot_all import plotAllFigs


# Get list of figs to plot from command line args.
if len(sys.argv) > 1:
    plot_list = sys.argv[1:]
else:
    plot_list = None


# Get plotting data
outputData = getFullData(default_prices, default_options)


# Run plotting routines to generate figures
figs = plotAllFigs(outputData, plots_cfg, plot_list=plot_list)


# Export figures to files
exportFigsToFiles(figs)
