from src.scaffolding.data.data import getFullData
from src.scaffolding.file.load_config_app import app_cfg
from src.scaffolding.file.load_config_plot import plots_cfg
from src.scaffolding.file.load_default_data import default_prices, default_options
from src.scaffolding.plotting.plot_all import plotAllFigs
from src.scaffolding.plotting.styling.webapp import addWebappSpecificStyling


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
figsDefault = plotAllFigs(outputData, inputData, plots_cfg, target='webapp', required_figs=figsNeeded)
addWebappSpecificStyling(figsDefault)
