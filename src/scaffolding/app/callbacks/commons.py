from src.scaffolding.file.load_config import plots

figNames = [figName for plot in plots.values() for figName in plot.getFigs()]
subfigsDisplayed = sorted([subfig for plot in plots.values() for subfig in plot.getAllSubfigs()])
