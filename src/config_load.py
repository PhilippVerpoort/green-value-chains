import yaml

from src.filepaths import getFilePathInput


# load input data for calculations
def loadYamlFile(fname: str):
    __filePath = getFilePathInput(fname)
    return yaml.load(open(__filePath, 'r').read(), Loader=yaml.FullLoader)

options = loadYamlFile('data/options.yml')
cost_data = loadYamlFile('data/cost_data.yml')
input_data = {**options, **cost_data}

default_assumptions = loadYamlFile('data/assumptions.yml')
units = loadYamlFile('data/units.yml')
ref_data = loadYamlFile('data/ref_data.yml')
cp_data = loadYamlFile('data/cp.yml')


# load config data for plots and figures
plots = loadYamlFile('plots.yml')
figure_print = loadYamlFile('figure_print.yml')
plots_cfg_global = loadYamlFile('plotting/global.yml')

plots_cfg = {
    plotName: open(getFilePathInput(f"plotting/{plotName}.yml"), 'r').read()
    for plotName in plots
}
