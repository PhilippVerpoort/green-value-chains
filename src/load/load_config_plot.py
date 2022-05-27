from src.load.file_paths import getFilePathInput
from src.load.yaml_load import loadYamlFile


# load config data for plots and figures
plots = loadYamlFile('plots.yml')
figure_print = loadYamlFile('figure_print.yml')
plots_cfg_global = loadYamlFile('plotting/global.yml')

plots_cfg = {
    plotName: open(getFilePathInput(f"plotting/{plotName}.yml"), 'r').read()
    for plotName in plots
}
