from typing import Union

import plotly.io as pio

from src.scaffolding.file.load_config import plots
from src.scaffolding.plotting.styling.template import defineTemplate


pio.templates['pik'] = defineTemplate()
pio.templates.default = "pik"


def plotAllFigs(input_data: dict, final_data: dict, plot_cfgs: dict, figs_req: Union[list, None] = None, target: str = 'print'):
    producedPlots = {}

    for plotName, plotClass in plots.items():
        plot = plotClass(input_data, final_data, figs_req, target, plot_cfgs[plotName])
        plot.produce()

        producedPlots[plotName] = plot

    return producedPlots


def exportFigs(producedPlots: dict):
    for plotName, plot in producedPlots.items():
        plot.export()


def getFigures(producedPlots: dict):
    r = {}

    for plotName, plot in producedPlots.items():
        r |= plot.display()

    return r
