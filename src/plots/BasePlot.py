from string import ascii_lowercase
from typing import Optional, Final

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb

from piw import AbstractPlot


inch_per_pt: Final[float] = 1 / 72

class BasePlot(AbstractPlot):
    _addSubfigName: bool = False
    _addSubfigNameDict: Optional[dict] = None

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        for subfigName, subfigPlot in subfigs.items():
            if subfigPlot is None: continue

            fs_sm = self.getFontSize('fs_sm')
            fs_md = self.getFontSize('fs_md')
            fs_lg = self.getFontSize('fs_lg')

            self._decorateFontAndLabels(subfigName, subfigPlot, fs_sm, fs_md, fs_lg)

    def _decorateFontAndLabels(self, subfigName: str, subfigPlot: go.Figure, fs_sm: float, fs_md: float, fs_lg: float):
        subfigPlot.update_layout(font_size=fs_sm)
        subfigPlot.update_xaxes(title_font_size=fs_sm, tickfont_size=fs_sm)
        subfigPlot.update_yaxes(title_font_size=fs_sm, tickfont_size=fs_sm)
        subfigPlot.update_annotations(font_size=fs_sm)

        # subplot labels
        if self._addSubfigName:
            if subfigName[-1] in ascii_lowercase:
                subfigNameDict = {1: subfigName[-1]}
            else:
                numSubPlots = self.__countNumbSubplots(subfigPlot)

                if self._addSubfigNameDict is None:
                    subfigNameDict = {i: ascii_lowercase[i] for i in range(numSubPlots)}
                else:
                    subfigNameDict = self._addSubfigNameDict

            for i, subfigLabel in subfigNameDict.items():
                subfigPlot.add_annotation(
                    showarrow=False,
                    text=f"<b>{subfigLabel}</b>",
                    font_size=fs_lg,
                    x=0.0,
                    xanchor='left',
                    xref=f"x{i + 1 if i else ''} domain",
                    y=1.0,
                    yanchor='bottom',
                    yref=f"y{i + 1 if i else ''} domain",
                    yshift=10.0,
                )

    def __countNumbSubplots(self, fig: go.Figure):
        return sum(1 for row in range(len(fig._grid_ref))
                   for col in range(len(fig._grid_ref[row]))
                   if fig._grid_ref[row][col] is not None) \
            if fig._grid_ref is not None else 1

    @staticmethod
    def _groupbySumval(df: pd.DataFrame, groupCols: list, keep: list = []) -> pd.DataFrame:
        if 'val_rel' in df.columns:
            raise Exception('Cannot sum relative values.')
        sumCols = [col for col in ['val', 'val_diff'] if col in df.columns]
        return df.groupby(groupCols) \
            .agg(dict(**{c: 'first' for c in groupCols + keep}, **{c: 'sum' for c in sumCols})) \
            .reset_index(drop=True)

    def _addAnnotation(self, fig: go.Figure, text: str, subplot_id: int):
        fig.add_annotation(
            text=f"<b>{text}</b>",
            x=1.0,
            xref=f"x{subplot_id + 1 if subplot_id else ''} domain",
            xanchor='right',
            y=1.0,
            yref=f"y{subplot_id + 1 if subplot_id else ''} domain",
            yanchor='top',
            showarrow=False,
            bordercolor='black',
            borderwidth=self._globCfg['globStyle'][self._target]['lw_ultrathin'],
            borderpad=2*self._globCfg['globStyle'][self._target]['lw_ultrathin'],
            bgcolor='white',
        )

    def _addAnnotationComm(self, fig: go.Figure, comm: str, c: int):
        fig.add_annotation(
            text=f"<b>{comm}</b>",
            x=0.5,
            xref='x domain',
            xanchor='center',
            y=1.0,
            yshift=30.0,
            yref='y domain',
            yanchor='bottom',
            showarrow=False,
            bordercolor=self._globCfg['globPlot']['commodity_colours'][comm],
            borderwidth=self._globCfg['globStyle'][self._target]['lw_thin'],
            borderpad=3*self._globCfg['globStyle'][self._target]['lw_thin'],
            bgcolor="rgba({}, {}, {}, {})".format(*hex_to_rgb(self._globCfg['globPlot']['commodity_colours'][comm]), .3),
            font_color=self._globCfg['globPlot']['commodity_colours'][comm],
            font_size=self.getFontSize('fs_lg'),
            row=1,
            col=c + 1,
        )

    @staticmethod
    def _updateAxisLayout(fig: go.Figure, i: int, xaxis: Optional[dict] = None, yaxis: Optional[dict] = None):
        if xaxis is not None:
            fig.update_layout(**{
                f"xaxis{i + 1 if i else ''}": xaxis,
            })
        if yaxis is not None:
            fig.update_layout(**{
                f"yaxis{i + 1 if i else ''}": yaxis,
            })

    def getFontSize(self, size: str):
        return self._dpi * inch_per_pt * self._globCfg['globStyle'][self._target][size]
