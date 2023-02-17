from abc import ABC, abstractmethod
from string import ascii_lowercase

import plotly.graph_objects as go
import yaml

from src.scaffolding.file.file_load import loadYAMLConfigFile
from src.scaffolding.file.file_path import pathOfOutputFile


class AbstractPlot(ABC):
    _complete = False
    _dpi = 300.0

    def __init__(self, input_data: dict, final_data: dict, required_figs: list, target: str, plot_cfg: dict):
        self._inputData = input_data
        self._finalData = final_data
        self._requiredFigs = required_figs
        self._target = target
        self._isWebapp = target=='webapp'

        # set complete config
        self._config = {
            **yaml.load(plot_cfg, Loader=yaml.FullLoader),
            **self.__globalConfig,
            **{'global': self.__globalStyling[target]}
        }

        self._prep = {}
        self._ret = {}

    @classmethod
    def isComplete(cls):
        return cls._complete

    @classmethod
    def loadGlobal(cls):
        cls.__globalConfig = loadYAMLConfigFile('globalConfig')
        cls.__globalStyling = loadYAMLConfigFile('globalStyling')

    @classmethod
    def loadSpecs(cls):
        cls._specs = loadYAMLConfigFile(f"figure_configs/{cls.__name__}")

        cls._sizes = {}
        for figName, figSpecs in cls._specs.items():
            if 'subfigs' in figSpecs:
                cls._sizes |= figSpecs['subfigs']
            else:
                cls._sizes[figName] = figSpecs['sizes']

    def getFigs(self):
        return [figName for figName in self._specs]

    def getSubfigs(self):
        r = []
        for figName, figSpecs in self._specs.items():
            if 'subfigs' in figSpecs:
                r.extend([subfigName for subfigName in figSpecs['subfigs']])
            else:
                r.append(figName)
        return r

    def anyRequired(self, *subfigs):
        if not self._requiredFigs: return True
        return any(f in self._requiredFigs for f in subfigs)

    def produce(self):
        self._prepare()
        self._plot()
        self._decorate()
        if self._isWebapp:
            self._addPlaceholders()

    @abstractmethod
    def _prepare(self):
        pass

    @abstractmethod
    def _plot(self):
        pass

    def _addPlaceholders(self):
        for subfigName in self.getSubfigs():
            if subfigName not in self._ret:
                f = go.Figure()
                f.add_annotation(
                    text='<b>Press GENERATE to<br>display this plot.</b>',
                    xanchor='center',
                    xref='x domain',
                    x=0.5,
                    yanchor='middle',
                    yref='y domain',
                    y=0.5,
                    showarrow=False,
                    bordercolor='black',
                    borderwidth=2,
                    borderpad=3,
                    bgcolor='white',
                )
                self._ret[subfigName] = f

    def _decorate(self):
        for subfigName, subfigPlot in self._ret.items():
            if subfigPlot is None: continue

            fs_sm = self._getFontSize('fs_sm')
            fs_md = self._getFontSize('fs_md')
            fs_lg = self._getFontSize('fs_lg')

            self.__adjustFontSizes(subfigName, subfigPlot, fs_sm, fs_md, fs_lg)

    def export(self):
        for subfigName, subfigPlot in self._ret.items():
            if subfigPlot is None: continue

            h_mm = self._sizes[subfigName]['print']['height']
            w_mm = self._sizes[subfigName]['print']['width']

            subfigPlot.write_image(pathOfOutputFile(f"{subfigName}.png"), **self.__getImageSize(h_mm, w_mm))

    @classmethod
    def __adjustFontSizes(cls, subfigName: str, subfigPlot: go.Figure, fs_sm: float, fs_md: float, fs_lg: float):
        subfigPlot.update_layout(font_size=fs_sm)
        subfigPlot.update_xaxes(title_font_size=fs_sm, tickfont_size=fs_sm)
        subfigPlot.update_yaxes(title_font_size=fs_sm, tickfont_size=fs_sm)
        subfigPlot.update_annotations(font_size=fs_sm)

        # subplot labels
        if subfigName not in []:
            numSubPlots = cls.__countNumbSubplots(subfigPlot)
            for i in range(numSubPlots):
                subfigLabel = subfigName[-1] if subfigName[-1] in ascii_lowercase else ascii_lowercase[i]

                if subfigName == 'fig5':
                    yref = f"y{2 * i + 1 if i else ''} domain" if i < 3 else f"y{i + 4 if i else ''} domain"
                else:
                    yref = f"y{i + 1 if i else ''} domain"

                subfigPlot.add_annotation(
                    showarrow=False,
                    text=f"<b>{subfigLabel}</b>",
                    font_size=fs_lg,
                    x=0.0,
                    xanchor='left',
                    xref=f"x{i + 1 if i else ''} domain",
                    y=1.0,
                    yanchor='bottom',
                    yref=yref,
                    yshift=10.0,
                )

    def __countNumbSubplots(figure: go.Figure):
        return sum(1 for row in range(len(figure._grid_ref))
                   for col in range(len(figure._grid_ref[row]))
                   if figure._grid_ref[row][col] is not None) \
            if figure._grid_ref is not None else 1

    def _getFontSize(self, size: str):
        inch_per_pt = 1 / 72
        return self._dpi * inch_per_pt * self.__globalStyling[self._target][size]

    @classmethod
    def __getImageSize(cls, height_mm: float, width_mm: float):
        inch_per_mm = 0.03937

        height_px = int(cls._dpi * inch_per_mm * height_mm)
        width_px = int(cls._dpi * inch_per_mm * width_mm)

        return dict(
            height=height_px,
            width=width_px,
        )

