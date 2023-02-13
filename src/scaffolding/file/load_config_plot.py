from src.scaffolding.file.file_path import pathOfConfigFile
from src.scaffolding.file.file_load import loadYAMLConfigFile


# load config data for plots and figures
plots = loadYAMLConfigFile('plots')
for plotName in plots:
    if isinstance(plots[plotName], list):
        plots[plotName] = {f: [f] for f in plots[plotName]}

figure_print = loadYAMLConfigFile('figure_config/print')

plots_cfg = {}
for plotName in plots:
    __filePath = pathOfConfigFile(f"plot_config/{plotName}.yml")
    plots_cfg[plotName] = open(__filePath, 'r').read()

plots_cfg_global = loadYAMLConfigFile('plot_config/globalConfig')
plots_cfg_styling = loadYAMLConfigFile('plot_config/globalStyling')
