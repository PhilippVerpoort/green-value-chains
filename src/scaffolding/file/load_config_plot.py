from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from src.scaffolding.file.file_path import pathOfConfigFile
from src.scaffolding.plotting.AbstractPlot import AbstractPlot


# load global
AbstractPlot.loadGlobal()


# import all plot classes and collect them in a dict
for (module_loader, name, ispkg) in iter_modules(['src/custom/plots']):
    import_module('src.custom.plots.' + name)
plots = {c.__name__: c for c in AbstractPlot.__subclasses__()}

plot_cfgs = {}
for plotName, plot in plots.items():
    plot.loadSpecs()
    __filePath = pathOfConfigFile(f"plot_configs/{plotName}.yml")
    plot_cfgs[plotName] = open(__filePath, 'r').read()
