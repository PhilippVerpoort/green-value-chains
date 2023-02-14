from typing import Union

import plotly.io as pio

from src.scaffolding.file.load_config_plot import plots
from src.scaffolding.plotting.styling.template import defineTemplate


pio.templates['pik'] = defineTemplate()
pio.templates.default = "pik"


def plotAllFigs(final_data: dict, plots_cfg: dict, required_figs: Union[list, None] = None, target: str = 'print'):
    producedPlots = {}

    for plotName, plotClass in plots.items():
        plot = plotClass(final_data, required_figs, target, plots_cfg[plotName])
        plot.produce()

        producedPlots[plotName] = plot

    return producedPlots


def exportFigs(producedPlots: dict):
    for plotName, plot in producedPlots.items():
        plot.export()
