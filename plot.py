import sys

from src.scaffolding.file.load_config_plot import plot_cfgs
from src.scaffolding.file.load_default_data import default_other_prices, default_options, default_elec_prices
from src.scaffolding.data.data import getFullData
from src.scaffolding.plotting.plot_all import plotAllFigs, exportFigs


# get list of figs to plot from command line args.
if len(sys.argv) > 1:
    figs_needed = sys.argv[1:]
else:
    figs_needed = None


# collect input data for calculations
inputData = {
    'other_prices': default_other_prices,
    'elec_prices': default_elec_prices,
    'options': default_options,
}


# obtain full computed output data from inputs
finalData = getFullData(inputData)


# run plotting routines to generate figures
producedPlots = plotAllFigs(inputData, finalData, plot_cfgs, required_figs=figs_needed)


# export figures to image files
exportFigs(producedPlots)
