from src.load.file_paths import getFilePathInput
from src.load.yaml_load import loadYamlFile


# load config data for plots and figures
plots = loadYamlFile('plots.yml')
for plotName in plots:
    if isinstance(plots[plotName], list):
        plots[plotName] = {f: [f] for f in plots[plotName]}

figure_print = loadYamlFile('figure_config/print.yml')

plots_cfg = {}
for plotName in plots:
    __filePath = getFilePathInput(f"plot_config/{plotName}.yml")
    plots_cfg[plotName] = open(__filePath, 'r').read()

plots_cfg_global = loadYamlFile('plot_config/globalConfig.yml')
plots_cfg_styling = loadYamlFile('plot_config/globalStyling.yml')
