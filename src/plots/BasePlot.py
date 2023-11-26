from abc import ABC
from string import ascii_lowercase
from typing import Optional, Final

import plotly.graph_objects as go
from plotly.colors import hex_to_rgb

from piw import AbstractPlot


inch_per_pt: Final[float] = 1 / 72


class BasePlot(AbstractPlot, ABC):
    _add_subfig_name: bool = False
    _add_subfig_name_dict: Optional[dict] = None

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        for subfig_name, subfig_plot in subfigs.items():
            if subfig_plot is None:
                continue

            fs_sm = self.get_font_size('fs_sm')
            fs_md = self.get_font_size('fs_md')
            fs_lg = self.get_font_size('fs_lg')

            self._decorate_font_and_labels(subfig_name, subfig_plot, fs_sm, fs_md, fs_lg)

    def _decorate_font_and_labels(self, subfig_name: str, subfig_plot: go.Figure,
                                  fontsize_small: float, fontsize_medium: float, fontsize_large: float):
        subfig_plot.update_layout(font_size=fontsize_small)
        subfig_plot.update_xaxes(title_font_size=fontsize_small, tickfont_size=fontsize_small)
        subfig_plot.update_yaxes(title_font_size=fontsize_small, tickfont_size=fontsize_small)
        subfig_plot.update_annotations(font_size=fontsize_small)

        # subplot labels
        if self._add_subfig_name:
            if subfig_name[-1] in ascii_lowercase:
                subfig_name_dict = {0: subfig_name[-1]}
            else:
                subfig_plot_nsubplots = _count_numb_subplots(subfig_plot)

                if self._add_subfig_name_dict is None:
                    subfig_name_dict = {i: ascii_lowercase[i] for i in range(subfig_plot_nsubplots)}
                else:
                    subfig_name_dict = self._add_subfig_name_dict

            for i, subfig_label in subfig_name_dict.items():
                subfig_plot.add_annotation(
                    showarrow=False,
                    text=f"<b>{subfig_label}</b>",
                    font_size=fontsize_large,
                    x=0.0,
                    xanchor='left',
                    xref=f"x{i + 1 if i else ''} domain",
                    y=1.0,
                    yanchor='bottom',
                    yref=f"y{i + 1 if i else ''} domain",
                    yshift=10.0,
                )

    def _add_annotation(self, fig: go.Figure, text: str, subplot_id: int):
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
            borderwidth=self._styles['lw_ultrathin'],
            borderpad=2*self._styles['lw_ultrathin'],
            bgcolor='white',
        )

    def _add_annotation_comm(self, fig: go.Figure, comm: str, c: int):
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
            bordercolor=self._glob_cfg['commodity_colours'][comm],
            borderwidth=self._styles['lw_thin'],
            borderpad=3*self._styles['lw_thin'],
            bgcolor="rgba({}, {}, {}, {})".format(*hex_to_rgb(
                self._glob_cfg['commodity_colours'][comm]), .3),
            font_color=self._glob_cfg['commodity_colours'][comm],
            font_size=self.get_font_size('fs_lg'),
            row=1,
            col=c + 1,
        )

    @staticmethod
    def _update_axis_layout(fig: go.Figure, i: int, xaxis: Optional[dict] = None, yaxis: Optional[dict] = None):
        if xaxis is not None:
            fig.update_layout(**{
                f"xaxis{i + 1 if i else ''}": xaxis,
            })
        if yaxis is not None:
            fig.update_layout(**{
                f"yaxis{i + 1 if i else ''}": yaxis,
            })

    def get_font_size(self, size: str):
        return self._dpi * inch_per_pt * self._styles[size]


def _count_numb_subplots(fig: go.Figure):
    grid_ref = fig._grid_ref
    return sum(1 for row in range(len(grid_ref))
               for col in range(len(grid_ref[row]))
               if grid_ref[row][col] is not None) \
        if grid_ref is not None else 1
