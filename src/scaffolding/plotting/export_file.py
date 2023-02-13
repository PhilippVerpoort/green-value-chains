from src.scaffolding.file.load_config_plot import figure_print
from src.scaffolding.file.file_path import pathOfOutputFile
from src.scaffolding.plotting.styling.print import getImageSize, addPrintSpecificStyling


def exportFigsToFiles(figs: dict):
    addPrintSpecificStyling(figs)

    for subfigName, plotlyFigure in figs.items():
        if plotlyFigure is None: continue

        w_mm, h_mm = figure_print[subfigName]['size']

        plotlyFigure.write_image(pathOfOutputFile(f"{subfigName}.png"), **getImageSize(w_mm, h_mm))
