import sys

from src.scaffolding.file.load_config import plot_cfgs
from src.scaffolding.file.load_data import default_input_data
from src.scaffolding.data.data import getFullData
from src.scaffolding.plotting.plot_all import plotAllFigs, exportFigs


# get list of figs to plot from command line args.
if len(sys.argv) > 1:
    figsReq = sys.argv[1:]
else:
    figsReq = None


# obtain full computed output data from inputs
finalData = getFullData(default_input_data)


# run plotting routines to generate figures
producedPlots = plotAllFigs(default_input_data, finalData, plot_cfgs, figs_req=figsReq, target='webapp')


# export figures to image files
exportFigs(producedPlots)
