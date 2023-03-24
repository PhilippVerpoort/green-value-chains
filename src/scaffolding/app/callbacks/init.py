from src.scaffolding.data.data import getFullData
from src.scaffolding.file.load_config import plot_cfgs, plots
from src.scaffolding.file.load_data import default_input_data
from src.scaffolding.plotting.plot_all import plotAllFigs, getFigures


# get list of figures initially needed from app config
figsReq = [figName for plot in plots.values() for figName in plot.getFigs() if '/' in plot.getFigSpecs(figName)['display']]


# obtain full computed output data from inputs
finalData = getFullData(default_input_data)


# run plotting routines to generate figures
initialPlots = plotAllFigs(default_input_data, finalData, plot_cfgs, figs_req=figsReq, target='webapp')
figsInit = getFigures(initialPlots)
