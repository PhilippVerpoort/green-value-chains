from importlib import import_module
from pkgutil import iter_modules

from src.scaffolding.file.file_path import pathOfConfigFile
from src.scaffolding.plotting.AbstractPlot import AbstractPlot


# load global
AbstractPlot.loadGlobal()


# import all plot classes and collect them in a dict
for (module_loader, name, ispkg) in iter_modules(['src/custom/plots']):
    import_module('src.custom.plots.' + name)
plots = {}
def addSubClasses(cls):
    for subclass in cls.__subclasses__():
        if subclass.isComplete():
            plots[subclass.__name__] = subclass
        addSubClasses(subclass)
addSubClasses(AbstractPlot)

plot_cfgs = {}
for plotName, plot in plots.items():
    plot.loadSpecs()
    __filePath = pathOfConfigFile(f"plot_configs/{plotName}.yml")
    plot_cfgs[plotName] = open(__filePath, 'r').read()
