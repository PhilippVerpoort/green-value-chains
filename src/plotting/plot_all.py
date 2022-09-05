from typing import Union
import importlib

import yaml

from src.load.load_config_plot import plots, plots_cfg_global, plots_cfg_styling


def plotAllFigs(outputData: dict, plots_cfg: dict, plot_list: Union[list, None] = None, global_cfg = 'print'):

    allPlotArgs = {
        'plotLevelisedCost': (outputData['costData'],),
        'plotValueCreation': (outputData['costData'],),
        'plotCostDiffElecPrice': (outputData['costData'], outputData['costDataRef'], outputData['prices'],),
    }

    figs = {}
    for i, plotName in enumerate(plots):
        if plot_list is not None and plotName not in plot_list:
            if isinstance(plots[plotName], list):
                figs.update({f"{fig}": None for fig in plots[plotName]})
            elif isinstance(plots[plotName], dict):
                figs.update({f"{subFig}": None for fig in plots[plotName] for subFig in plots[plotName][fig]})
            else:
                raise Exception('Unknown figure type.')

        else:
            print(f"Plotting {plotName}...")
            plotArgs = allPlotArgs[plotName]
            config = yaml.load(plots_cfg[plotName], Loader=yaml.FullLoader)
            if 'import' in config:
                for imp in config['import']:
                    config[imp] = yaml.load(plots_cfg[imp], Loader=yaml.FullLoader)
            config = {**config, **yaml.load(plots_cfg[plotName], Loader=yaml.FullLoader), **plots_cfg_global, **{'global': plots_cfg_styling[global_cfg]}}

            module = importlib.import_module(f"src.plotting.plots.{plotName}")
            plotFigMethod = getattr(module, plotName)

            newFigs = plotFigMethod(*plotArgs, config)
            figs.update(newFigs)

    print('Done with plotting...')

    return figs
