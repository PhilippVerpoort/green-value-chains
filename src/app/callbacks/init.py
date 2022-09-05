from src.data.data import getFullData
from src.load.load_config_app import app_cfg
from src.load.load_config_plot import plots_cfg
from src.load.load_default_data import default_prices, default_options
from src.plotting.plot_all import plotAllFigs
from src.plotting.styling.webapp import addWebappSpecificStyling


# get list of figures initially needed from app config
figsNeeded = [fig for fig, routes in app_cfg['figures'].items() if '/' in routes]


# collect input data for calculations
inputData = {
    'prices': default_prices,
    'options': default_options,
}


# obtain full computed output data from inputs
outputData = getFullData(inputData)


# run plotting routines to generate figures
figsDefault = plotAllFigs(outputData, inputData, plots_cfg, global_cfg='webapp', figs_needed=figsNeeded)
addWebappSpecificStyling(figsDefault)
