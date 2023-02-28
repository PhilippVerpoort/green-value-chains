import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.colors import hex_to_rgb

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import commodities


class TotalCostPlot(BasePlot):
    _complete = True

    def _prepare(self):
        if self.anyRequired('fig3'):
            self._prep = {}
            self._prep |= self.__prepareData(self._finalData['costData'])
            self._prep |= self.__prepareHeatmap(self._prep['costDataCases'])


    # make adjustments to data (route names, component labels)
    def __prepareData(self, costData: pd.DataFrame):
        # remove upstream cost entries and drop non-case routes
        costDataNew = costData \
            .query(f"type!='upstream' and case.notnull()") \
            .reset_index(drop=True)

        # select period and drop column
        costDataNew = costDataNew \
            .query(f"period=={self._config['select_period']}") \
            .drop(columns=['period'])

        # insert final electricity prices
        costDataCases = self._finaliseCostData(costDataNew, epdcases=['upper', 'default', 'lower'], epperiod=self._config['select_period'])

        # aggregate cost data split by transport part and other parts
        costDataCases = pd.merge(
                self._groupbySumval(costDataCases.query("type=='transport'"), ['commodity', 'case', 'epdcase'], keep=['epdiff']),
                self._groupbySumval(costDataCases.query("type!='transport'").fillna({'component': 'empty'}), ['commodity', 'case', 'epdcase'], keep=['epdiff']),
                on=['commodity', 'case', 'epdcase', 'epdiff'],
                how='outer',
                suffixes=('_transp', '_other'),
            )\
            .fillna(0.0) \
            .assign(val=lambda x: x.val_transp + x.val_other)

        # add differences to Base Case
        costDataCases = costDataCases \
            .merge(costDataCases.query(f"case=='Base Case'").filter(['commodity', 'epdcase', 'val', 'val_transp', 'val_other']), on=['commodity', 'epdcase'], suffixes=('', '_base')) \
            .assign(
                val_rel=lambda x: x.val / x.val_base,
                val_transp_penalty=lambda x: x.val_transp - x.val_transp_base,
                val_cost_saving=lambda x: x.val_other_base - x.val_other,
            ) \
            .drop(columns=['val_other', 'val_transp', 'val_base', 'val_other_base', 'val_transp_base'])

        return {
            'costDataCases': costDataCases,
        }


    def __prepareHeatmap(self, costDataCases: pd.DataFrame):
        heatmap = {}
        axes = {}

        for c, comm in enumerate(commodities):
            costDataComm = costDataCases.query(f"commodity=='{comm}'").reset_index(drop=True)

            dataRange = {
                'xmin': costDataComm.val_cost_saving.min(), 'xmax': costDataComm.val_cost_saving.max(),
                'ymin': costDataComm.val_transp_penalty.min(), 'ymax': costDataComm.val_transp_penalty.max(),
            }

            xRange = [0.0, 1.1 * dataRange['xmax']]
            yRange = [-10.0 if comm=='Steel' else 0.0, 1.1 * dataRange['ymax']]

            x = np.linspace(*xRange, self._config['bottom']['samples'])
            y = np.linspace(*yRange, self._config['bottom']['samples'])
            vx, vy = np.meshgrid(x, y)
            z = (vx - vy) / costDataComm.query(f"case=='Base Case' and epdcase=='default'").iloc[0].val * 100

            heatmap[comm] = {
                'x': x,
                'y': y,
                'z': z,
            }

            axes[comm] = {
                'xaxis': dict(range=xRange),
                'yaxis': dict(range=yRange, domain=[0.0, 0.56]),
            }

        return {
            'axes': axes,
            'heatmap': heatmap,
        }


    def _plot(self):
        # produce fig3
        if self.anyRequired('fig3'):
            self._ret['fig3'] = self.__makePlot(**self._prep)

        return self._ret


    def __makePlot(self, costDataCases: pd.DataFrame, axes: dict, heatmap: dict):
        # create figure
        fig = make_subplots(
            cols=len(commodities),
            rows=2,
            horizontal_spacing=0.05,
        )


        # loop over commodities (three columns)
        for c, comm in enumerate(commodities):
            costDataComm = costDataCases\
                .query(f"commodity=='{comm}'")\
                .reset_index(drop=True)

            # add plots to top row
            self.__addTop(fig, c, comm, costDataComm)

            # add dashed hline top
            fig.add_hline(100.0, row=1, col=c+1, line_dash='dash', line_color='black')

            # update top axes layout
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(categoryorder='category ascending'),
                yaxis=dict(range=self._config['top']['yrange'], showticklabels=False, domain=[0.68, 1.0]),
            )

            # add plots to bottom row
            self.__addBottom(fig, c, comm, costDataComm, heatmap[comm])

            # update bottom axes layout
            self._updateAxisLayout(fig, c + 3, **axes[comm])

            # add commodity annotations above subplot
            self._addAnnotationComm(fig, c, comm)


        # update layout
        fig.update_layout(
            showlegend=False,
            legend_title='',
            yaxis_title=self._config['top']['yaxislabel'],
            yaxis_showticklabels=True,
            xaxis5_title=self._config['bottom']['xaxislabel'],
            yaxis4_title=self._config['bottom']['yaxislabel'],
        )


        return fig


    def __addTop(self, fig: go.Figure, c: int, comm: str, costDataComm: pd.DataFrame):
        # display cases 1A and 1B as same x
        costDataComm = costDataComm \
            .assign(displayCase=lambda r: r.case) \
            .replace({'displayCase': ['Case 1A', 'Case 1B']}, 'Case 1A/B')


        # middle line
        costDataCorridor = {
            epdcase: costDataComm.query(f"epdcase=='{epdcase}' and case!='Case 1A'").sort_values(by='case')
            for epdcase in costDataComm.epdcase.unique()
        }
        fig.add_trace(
            go.Scatter(
                x=costDataCorridor['default'].displayCase,
                y=costDataCorridor['default'].val_rel * 100,
                name=comm,
                mode='lines',
                line=dict(
                    shape='spline',
                    color=self._config['commodity_colours'][comm],
                ),
                showlegend=False,
                legendgroup=comm,
            ),
            row=1,
            col=c + 1,
        )

        # outside corridor
        fig.add_trace(
            go.Scatter(
                x=np.concatenate((costDataCorridor['upper'].displayCase[::-1], costDataCorridor['lower'].displayCase)),
                y=np.concatenate((costDataCorridor['upper'].val_rel[::-1], costDataCorridor['lower'].val_rel)) * 100,
                mode='lines',
                line=dict(
                    shape='spline',
                    width=0.0,
                ),
                fillcolor=("rgba({}, {}, {}, {})".format(*hex_to_rgb(self._config['commodity_colours'][comm]), .3)),
                fill='toself',
                showlegend=False,
                legendgroup=comm,
                hoverinfo='none',
            ),
            row=1,
            col=c + 1
        )

        # points
        costDataComm = costDataComm.query(f"case!='Base Case' or epdcase=='default'")
        for case in costDataComm.case.unique():
            thisData = costDataComm.query(f"case=='{case}'")
            fig.add_trace(
                go.Scatter(
                    x=thisData.displayCase,
                    y=thisData.val_rel * 100,
                    name=comm,
                    mode='markers+lines',
                    marker=dict(
                        color=self._config['commodity_colours'][comm],
                        symbol=self._config['symbol'],
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color=self._config['commodity_colours'][comm],
                    ),
                    showlegend=(case=='Base Case'),
                    legendgroup=comm,
                ),
                row=1,
                col=c + 1,
            )

        # annotations
        costDataComm = costDataComm.query(f"case=='Case 3'")
        fig.add_trace(
            go.Scatter(
                x=costDataComm.displayCase,
                y=costDataComm.val_rel * 100,
                text=costDataComm.epdiff,
                name=comm,
                mode='markers+text',
                textposition='middle right',
                textfont_size=self._getFontSize('fs_tn'),
                textfont_color=self._config['commodity_colours'][comm],
                marker_size=self._config['global']['marker_sm'],
                marker_color='rgba(0,0,0,0)',
                showlegend=False,
                legendgroup=comm,
            ),
            row=1,
            col=c + 1,
        )


    def __addBottom(self, fig: go.Figure, c: int, comm: str, costDataComm: pd.DataFrame, heatmapLinspaces: dict):
        # points
        for case in costDataComm.case.unique():
            if case == 'Base Case': continue
            thisData = costDataComm.query(f"case=='{case}'")

            # add points
            fig.add_trace(
                go.Scatter(
                    x=thisData.val_cost_saving,
                    y=thisData.val_transp_penalty,
                    text=thisData.case,
                    name=comm,
                    mode='markers+lines',
                    marker=dict(
                        color=self._config['commodity_colours'][comm],
                        symbol=self._config['symbol'],
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color=self._config['commodity_colours'][comm],
                    ),
                    showlegend=False,
                    legendgroup=comm,
                ),
                row=2,
                col=c + 1,
            )

            # epd annotations
            epdcaseDiff = thisData.query(f"case in ['Case 1A', 'Case 1B', 'Case 2']")
            fig.add_trace(
                go.Scatter(
                    x=epdcaseDiff.val_cost_saving,
                    y=epdcaseDiff.val_transp_penalty,
                    text=epdcaseDiff.epdiff,
                    name=comm,
                    mode='markers+text',
                    textposition='bottom center',
                    textfont_size=self._getFontSize('fs_tn'),
                    textfont_color=self._config['commodity_colours'][comm],
                    marker_size=self._config['global']['marker_sm'],
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    legendgroup=comm,
                ),
                row=2,
                col=c + 1,
            )

            # case annotations
            caseName = thisData.query(f"epdcase=='default'")
            fig.add_trace(
                go.Scatter(
                    x=caseName.val_cost_saving,
                    y=caseName.val_transp_penalty,
                    text=caseName.case,
                    name=comm,
                    mode='markers+text',
                    textposition='top center',
                    textfont_size=self._getFontSize('fs_sm'),
                    textfont_color=self._config['commodity_colours'][comm],
                    marker_size=self._config['global']['marker_sm'],
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    legendgroup=comm,
                ),
                row=2,
                col=c + 1,
            )

        # heatmap
        fig.add_trace(
            go.Heatmap(
                x=heatmapLinspaces['x'],
                y=heatmapLinspaces['y'],
                z=heatmapLinspaces['z'],
                zsmooth='best',
                zmin=self._config['bottom']['zrange'][0],
                zmax=self._config['bottom']['zrange'][1],
                colorscale=[
                    [i/(len(self._config['bottom']['zcolours'])-1), colour]
                    for i, colour in enumerate(self._config['bottom']['zcolours'])
                ],
                colorbar=dict(
                    x=1.01,
                    y=(0.5-0.05)/2,
                    yanchor='middle',
                    len=(0.5-0.025/2),
                    title=self._config['bottom']['zaxislabel'],
                    titleside='right',
                    tickvals=[float(t) for t in self._config['bottom']['zticks']],
                    ticktext=self._config['bottom']['zticks'],
                ),
                showscale=not c,
                hoverinfo='skip',
            ),
            row=2,
            col=c + 1,
        )

        # contour
        if self._config['contourLines']:
            fig.add_trace(
                go.Contour(
                    x=heatmapLinspaces['x'],
                    y=heatmapLinspaces['y'],
                    z=heatmapLinspaces['z'],
                    contours_coloring='lines',
                    colorscale=[
                        [0.0, '#000000'],
                        [1.0, '#000000'],
                    ],
                    line_width=self._config['global']['lw_ultrathin']/2,
                    contours=dict(
                        showlabels=False,
                        start=self._config['bottom']['zrange'][0],
                        end=self._config['bottom']['zrange'][1],
                        size=10.0,
                    ),
                    showscale=False,
                    hoverinfo='skip',
                ),
                row=2,
                col=c + 1,
            )

        # add center line
        fig.add_trace(
            go.Scatter(
                x=[-1000.0, +2000.0],
                y=[-1000.0, +2000.0],
                mode='lines',
                line=dict(
                    color='black',
                    width=self._config['global']['lw_thin'],
                    dash='dash',
                ),
                showlegend=False,
            ),
            row=2,
            col=c + 1,
        )
