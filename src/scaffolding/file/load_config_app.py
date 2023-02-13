import yaml

from src.scaffolding.file.load_config_plot import plots
from src.scaffolding.file.file_path import pathOfConfigFile
from src.scaffolding.file.file_load import loadYAMLConfigFile


# load config for webapp
app_cfg = loadYAMLConfigFile('webapp')


# generate lists of figure names and subfigure names from config
figNames = [figName for plotName in plots for figName in plots[plotName]]
subfigsDisplayed = []
for plotName in plots:
    for figName in plots[plotName]:
        if figName in app_cfg['figures']:
            subfigsDisplayed.extend(plots[plotName][figName])


# load display configs of figures in webapp
__filePath = pathOfConfigFile(f"figure_config/webapp.yml")
figs_cfg = yaml.load(open(__filePath, 'r').read(), Loader=yaml.FullLoader)
