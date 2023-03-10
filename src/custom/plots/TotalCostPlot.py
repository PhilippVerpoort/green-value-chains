import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.colors import hex_to_rgb

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import commodities


class TotalCostPlot(BasePlot):
    _complete = True

    def _decorate(self):
        super(TotalCostPlot, self)._decorate()

        # loop over commodities (three columns)
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for fig in self._ret.values():
                self._addAnnotationComm(fig, c, comm)


    def _prepare(self):
        if self.anyRequired('fig4'):
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
        costDataCases = self._finaliseCostData(costDataNew, epdcases=['strong', 'medium', 'weak'], epperiod=self._config['select_period'])

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
                val_rel=lambda x: (x.val / x.val_base) * 100.0,
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

            plotRange = [
                -10.0 if comm == 'Steel' else 0.0,
                1.1*max(dataRange['xmax'], dataRange['ymax']),
            ]

            x = np.linspace(*plotRange, self._config['bottom']['samples'])
            y = np.linspace(*plotRange, self._config['bottom']['samples'])
            vx, vy = np.meshgrid(x, y)
            z = ((vx - vy) / costDataComm.query(f"case=='Base Case' and epdcase=='medium'").iloc[0].val) * 100.0

            heatmap[comm] = {
                'x': x,
                'y': y,
                'z': z,
            }

            axes[comm] = {
                'xaxis': dict(range=plotRange),
                'yaxis': dict(range=plotRange, domain=[0.0, self._config['bottom']['domain_boundary']]),
            }

        return {
            'axes': axes,
            'heatmap': heatmap,
        }


    def _plot(self):
        # produce fig3
        if self.anyRequired('fig4'):
            self._ret['fig4'] = self.__makePlot(**self._prep)

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

            # add zeroline top
            fig.add_hline(100.0, row=1, col=c+1, line_color='black')

            # update top axes layout
            xrange = [i*(costDataComm.case.nunique()-2) + 0.2 * (+1 if i else -1) for i in range(2)]
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(categoryorder='category ascending', range=xrange),
                yaxis=dict(domain=[self._config['top']['domain_boundary'], 1.0], **self._config['top']['yaxis'], showticklabels=False),
            )

            # add plots to bottom row
            self.__addBottom(fig, c, comm, costDataComm, heatmap[comm])

            # update bottom axes layout
            self._updateAxisLayout(fig, c + 3, **axes[comm])


        # add dummy data for legend
        self.__addDummyLegend(fig)


        # update layout
        fig.update_layout(
            showlegend=True,
            legend=dict(
                title='',
                x=1.01,
                xanchor='left',
                y=self._config['bottom']['domain_boundary'],
                yanchor='top',
            ),
            yaxis_title=self._config['top']['yaxislabelleft'],
            yaxis_showticklabels=True,
            xaxis5_title=self._config['bottom']['xaxislabel'],
            yaxis4_title=self._config['bottom']['yaxislabel'],
        )


        return fig


    def __addDummyLegend(self, fig: go.Figure):
        for legend, symbol in [('Case 1A', self._config['symbolCase1A']), ('Other cases', self._config['symbol'])]:
            fig.add_trace(
                go.Scatter(
                    x=[-1000.0],
                    y=[-1000.0],
                    name=legend,
                    mode='markers+lines',
                    marker=dict(
                        color='black',
                        symbol=symbol,
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color='black',
                    ),
                    showlegend=True,
                    legendgroup='dummy',
                ),
                row=2,
                col=1,
            )


    def __addTop(self, fig: go.Figure, c: int, comm: str, costDataComm: pd.DataFrame):
        # display cases 1A and 1B as same x
        costDataComm = costDataComm \
            .assign(displayCase=lambda r: r.case) \
            .replace({'displayCase': ['Case 1A', 'Case 1B']}, 'Case 1A/B') \
            .replace({'displayCase': {caseName: f"<b>{caseName}</b>:<br>{caseDesc}" for caseName, caseDesc in self._config['case_names'].items()}})


        # middle line
        costDataCorridor = {
            epdcase: costDataComm.query(f"epdcase=='{epdcase}' and case!='Case 1A'").sort_values(by='case')
            for epdcase in costDataComm.epdcase.unique()
        }
        fig.add_trace(
            go.Scatter(
                x=costDataCorridor['medium'].displayCase,
                y=costDataCorridor['medium'].val_rel,
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
                x=np.concatenate((costDataCorridor['strong'].displayCase[::-1], costDataCorridor['weak'].displayCase)),
                y=np.concatenate((costDataCorridor['strong'].val_rel[::-1], costDataCorridor['weak'].val_rel)),
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
        costDataComm = costDataComm.query(f"case!='Base Case' or epdcase=='medium'")
        for case in costDataComm.case.unique():
            thisData = costDataComm.query(f"case=='{case}'")
            fig.add_trace(
                go.Scatter(
                    x=thisData.displayCase,
                    y=thisData.val_rel,
                    name=comm,
                    mode='markers+lines',
                    marker=dict(
                        color=self._config['commodity_colours'][comm],
                        symbol=self._config['symbolCase1A'] if case == 'Case 1A' else self._config['symbol'],
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color=self._config['commodity_colours'][comm],
                    ),
                    showlegend=False,
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
                y=costDataComm.val_rel,
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

        # secondary axis
        if c==2:
            fig.add_trace(
                go.Scatter(
                    x=[costDataComm.displayCase.unique()[0]],
                    y=[+10000.0],
                    mode='markers',
                    showlegend=False,
                    xaxis='x3',
                    yaxis='y7',
                ),
            )

            fig.update_layout(
                yaxis7=dict(
                    title=self._config['top']['yaxislabelright'],
                    anchor='x3',
                    overlaying='y',
                    side='right',
                    range=[t-100.0 for t in self._config['top']['yaxis']['range']],
                ),
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
                    name=comm,
                    mode='markers+lines',
                    marker=dict(
                        color=self._config['commodity_colours'][comm],
                        symbol=self._config['symbolCase1A'] if case == 'Case 1A' else self._config['symbol'],
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
        colbarlen = 3/4 * self._config['bottom']['domain_boundary']
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
                    y=colbarlen/2,
                    yanchor='middle',
                    len=colbarlen,
                    title=self._config['bottom']['zaxislabel'],
                    titleside='right',
                    tickvals=[float(t) for t in self._config['bottom']['zticks']],
                    ticktext=self._config['bottom']['zticks'],
                    titlefont_size=self._getFontSize('fs_sm'),
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
                x=[-1000.0, +10000.0],
                y=[-1000.0, +10000.0],
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
