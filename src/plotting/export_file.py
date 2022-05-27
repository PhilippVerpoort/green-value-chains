from src.load.load_config_plot import figure_print
from src.load.file_paths import getFilePathOutput
from src.plotting.styling.print import getImageSize, addPrintSpecificStyling


def exportFigsToFiles(figs: dict):
    addPrintSpecificStyling(figs)

    for subfigName, plotlyFigure in figs.items():
        if plotlyFigure is None: continue

        w_mm, h_mm = figure_print[subfigName]['size']

        plotlyFigure.write_image(getFilePathOutput(f"{subfigName}.png"), **getImageSize(w_mm, h_mm))
