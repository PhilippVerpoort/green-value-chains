import yaml

from src.load.load_config_plot import plots
from src.load.file_paths import getFilePathInput
from src.load.yaml_load import loadYamlFile


# load config for app
app_cfg = loadYamlFile('app.yml')


# generate lists of figure names and subfigure names from config
figNames = [figName for plotName in plots for figName in plots[plotName]]
allSubFigNames = []
for plotName in plots:
    for figName in plots[plotName]:
        if isinstance(plots[plotName], list):
            allSubFigNames.append(figName)
        else:
            allSubFigNames.extend(plots[plotName][figName])


# load figures config
figs_cfg = {}
for plotName in plots:
    for figName in plots[plotName]:
        __filePath = getFilePathInput(f"figures/{figName}.yml")
        figs_cfg[figName] = yaml.load(open(__filePath, 'r').read(), Loader=yaml.FullLoader)
