from src.scaffolding.file.load_config_plot import plots
from src.scaffolding.file.file_load import loadYAMLConfigFile


# load config for webapp
app_cfg = loadYAMLConfigFile('webapp')


# generate lists of figure names and subfigure names from config
figNames = []
subfigsDisplayed = []
for plotName, plotClass in plots:
    figNames.extend(plotClass.getFigs())
    subfigsDisplayed.extend(plotClass.getSubfigs())
