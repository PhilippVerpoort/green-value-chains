import sys

from src.scaffolding.file.load_default_data import default_prices, default_options
from src.scaffolding.file.load_config_plot import plots_cfg
from src.scaffolding.data.data import getFullData
from src.scaffolding.plotting.export_file import exportFigsToFiles
from src.scaffolding.plotting.plot_all import plotAllFigs


# get list of figs to plot from command line args.
if len(sys.argv) > 1:
    figs_needed = sys.argv[1:]
else:
    figs_needed = None


# collect input data for calculations
inputData = {
    'prices': default_prices,
    'options': default_options,
}


# obtain full computed output data from inputs
outputData = getFullData(inputData)


# run plotting routines to generate figures
figs = plotAllFigs(outputData, inputData, plots_cfg, figs_needed=figs_needed)


# export figures to files
exportFigsToFiles(figs)
