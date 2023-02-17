import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import commodities


class SensitivityPlot(BasePlot):
    _complete = True

    def _prepare(self):
        if self.anyRequired('fig6'):
            self._prep = self.__makePrep(
                self._finalData['costData'],
                self._finalData['techCostH2Transp'],
            )


    # make adjustments to data
    def __makePrep(self, costData: pd.DataFrame, techCostH2Transp: pd.DataFrame):
        # remove upstream cost entries and drop non-case routes
        costDataNew = costData \
            .query(f"type!='upstream' and case.notnull()") \
            .reset_index(drop=True)

        # select period and drop column
        costDataNew = costDataNew \
            .query(f"period=={self._config['select_period']}") \
            .drop(columns=['period'])

        # multiply by electricity prices and aggregate
        tmp = self._finaliseCostData(costDataNew, epperiod=self._config['select_period'])
        costDataCases = self._groupbySumval(tmp, ['commodity', 'case', 'epdcase'], keep=['route', 'baseRoute', 'epdiff'])

        # add differences to Base Case
        costDataCases = costDataCases \
            .merge(costDataCases.query(f"case=='Base Case'").filter(['commodity', 'epdcase', 'val']), on=['commodity', 'epdcase'], suffixes=('', '_base')) \
            .assign(val_diff=lambda x: x.val - x.val_base) \
            .drop(columns=['val_base'])

        # transportation cost for hydrogen
        tmp = costDataNew.query("type=='transport' and component=='hydrogen'")
        costH2Transp = self._groupbySumval(tmp, ['commodity', 'case'], keep=['route', 'baseRoute']) \
            .rename(columns={'val': 'costH2Transp'})

        # base H2 transportation cost
        specH2TranspCost = techCostH2Transp \
            .query(f"period=={self._config['select_period']}") \
            .filter(['mode', 'val']) \
            .rename(columns={'val': 'specH2TranspCost', 'mode': 'case'}) \
            .replace({'case': {'shipping': 'Case 1A', 'pipeline': 'Case 1B'}})

        # merge all for interpolation
        merge = costDataCases.query(f"epdcase=='max'") \
            .merge(costDataCases.query(f"epdcase=='zero'"), on=['commodity', 'case', 'route', 'baseRoute'], suffixes=('_max', '_zero')) \
            .merge(costH2Transp, on=['commodity', 'route', 'case', 'baseRoute'], how='left') \
            .merge(specH2TranspCost, on=['case'], how='left')

        # get ranges
        xrange = [costDataCases['epdiff'].min(), costDataCases['epdiff'].max()]
        yrange = {}
        for comm in commodities:
            vd = costDataCases.query(f"commodity=='{comm}'")['val_diff']
            yrange[comm] = [vd.min(), vd.max()]

        # linear interpolation of cost difference as a function of elec price
        epd_samp = np.linspace(*xrange, self._config['samples'])
        htc_samp = np.linspace(self._config['bottom']['yrange'][0], self._config['bottom']['yrange'][1], self._config['samples'])
        epd_mesh, htc_mesh = np.meshgrid(epd_samp, htc_samp)

        cases = costData.case.unique()

        plotData = {
            'top': {comm: {} for comm in commodities},
            'bottom': {},
        }
        for comm in commodities:
            baseCost = costDataCases.query(f"commodity=='{comm}' & case=='Base Case' & epdcase=='default'").iloc[0].val

            for case in cases:
                r = merge.query(f"commodity=='{comm}' & case=='{case}'").iloc[0]

                plotData['top'][comm][case] = r.val_diff_zero + (epd_samp - r.epdiff_zero)/(r.epdiff_max - r.epdiff_zero) * (r.val_diff_max - r.val_diff_zero)

                if case in ['Case 1A', 'Case 1B']:
                    plotData['bottom'][comm] = (
                        r.val_diff_zero + (epd_mesh - r.epdiff_zero)/(r.epdiff_max - r.epdiff_zero) * (r.val_diff_max - r.val_diff_zero)\
                      + r.costH2Transp * (htc_mesh / r.specH2TranspCost - 1.0)
                    ) / baseCost * 100.0

        return {
            'costDataCases': costDataCases.query(f"epdcase in ['upper', 'default', 'lower']"),
            'xrange': xrange,
            'yrange': yrange,
            'epd_samp': epd_samp,
            'htc_samp': htc_samp,
            'plotData': plotData,
            'specH2TranspCost': specH2TranspCost,
        }


    def _plot(self):
        # make fig5
        if self.anyRequired('fig6'):
            self._ret['fig6'] = self.__makePlot(**self._prep)


    def __makePlot(self, costDataCases: pd.DataFrame, xrange: list, yrange: dict,
                   epd_samp: np.ndarray, htc_samp: np.ndarray, plotData: dict, specH2TranspCost: pd.DataFrame):

        # create figure
        fig = make_subplots(
            rows=2,
            cols=len(commodities),
            # shared_yaxes=True,
            horizontal_spacing=0.035,
            vertical_spacing=0.08,
            # specs=[len(commodities) * [{"secondary_y": True}], len(commodities) * [{}]],
        )


        # plot heatmaps and contours
        for c, comm in enumerate(commodities):
            costDataComm = costDataCases\
                .query(f"commodity=='{comm}'")\
                .reset_index(drop=True)
            epdiffLines = costDataComm.epdiff.unique().tolist()

            # add plots to top row
            self.__addTop(fig, c, comm, epd_samp, plotData['top'][comm], costDataComm)

            # update top axes layout
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(range=xrange, showticklabels=False),
                yaxis=dict(range=yrange[comm]),
            )

            # add plots to bottom row
            self.__addBottom(c, comm, fig, epd_samp, htc_samp, plotData['bottom'][comm], costDataComm, specH2TranspCost)

            # update bottom axes layout
            self._updateAxisLayout(
                fig, c+3,
                xaxis=dict(range=xrange),
                yaxis=dict(range=self._config['bottom']['yrange'], showticklabels=False),
            )

            # add annotation above subplot
            self._addAnnotation(fig, c, 'Case 1 only', row=2)

            # add commodity annotations above subplot
            self._addAnnotationComm(fig, c, comm)


        # update layout
        fig.update_layout(
            xaxis5_title=f"{self._config['xaxislabel']}",
            yaxis=dict(title=self._config['top']['yaxislabel'], showticklabels=True),
            yaxis4=dict(title=self._config['bottom']['yaxislabel'], showticklabels=True),
        )


        return fig


    def __addTop(self, fig: go.Figure, c: int, comm: str, epd_samples: np.ndarray, plotData: dict,
                 costDataComm: pd.DataFrame):
        # add dashed vlines in the background
        for epdiff in costDataComm.epdiff.unique():
            fig.add_trace(
                go.Scatter(
                    x=[epdiff, epdiff],
                    y=[-10000, +10000],
                    showlegend=False,
                    hoverinfo='skip',
                    mode='lines',
                    line_color='#cccccc',
                    line_dash='dash',
                ),
                row=1,
                col=c + 1,
            )

        # loop over cases
        for case, caseData in plotData.items():
            if case in ['Base Case']:
                continue

            # add lines
            fig.add_trace(
                go.Scatter(
                    x=epd_samples,
                    y=caseData,
                    mode='lines',
                    name=case,
                    legendgroup=case,
                    showlegend=not c,
                    line=dict(
                        color=self._config['line_colour'][case],
                        width=self._config['global']['lw_thin'],
                        dash='dash' if case=='Case 1A' else 'solid',
                    ),
                    hovertemplate=f"<b>{case}</b><br>{self._config['xlabelshort']}: %{{x:.2f}}<br>{self._config['bottom']['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                row=1,
                col=c + 1,
            )

            # add points
            thisData = costDataComm.query(f"case=='{case}'")
            fig.add_trace(
                go.Scatter(
                    x=thisData.epdiff,
                    y=thisData.val_diff,
                    mode='markers',
                    text=thisData.case,
                    name=case,
                    legendgroup=case,
                    showlegend=False,
                    marker=dict(
                        color=self._config['line_colour'][case],
                        symbol=self._config['symbol'],
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color=self._config['line_colour'][case],
                    ),
                ),
                row=1,
                col=c + 1,
            )

            # add second yaxis
            # fig.add_trace(
            #     go.Scatter(x=self._config["xrange"], y=[-10, -10], showlegend=False),
            #     secondary_y=True,
            #     row=1,
            #     col=i + 1,
            # )


    def __addBottom(self, c: int, comm: str, fig: go.Figure, epd_samp: np.ndarray, htc_samp: np.ndarray,
                    plotData: dict, costDataComm: pd.DataFrame, specH2TranspCost: pd.DataFrame):
        fig.add_trace(
            go.Heatmap(
                x=epd_samp,
                y=htc_samp,
                z=plotData,
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

        fig.add_trace(
            go.Contour(
                x=epd_samp,
                y=htc_samp,
                z=plotData,
                contours_coloring='lines',
                colorscale=[
                    [0.0, '#000000'],
                    [1.0, '#000000'],
                ],
                line_width=self._config['global']['lw_thin'],
                contours=dict(
                    showlabels=True,
                    start=self._config['bottom']['zrange'][0],
                    end=self._config['bottom']['zrange'][1],
                    size=self._config['bottom']['zdelta'],
                ),
                showscale=False,
                hoverinfo='skip',
            ),
            row=2,
            col=c + 1,
        )

        # add dashed vlines in the background
        for epdiff in costDataComm.epdiff.unique():
            fig.add_trace(
                go.Scatter(
                    x=[epdiff, epdiff],
                    y=[-10000, +10000],
                    showlegend=False,
                    hoverinfo='skip',
                    mode='lines',
                    line_color='#cccccc',
                    line_dash='dash',
                ),
                row=2,
                col=c + 1,
            )

        # add Case 1 lines and points
        for case in ['Case 1A', 'Case 1B']:
            y = specH2TranspCost.query(f"case=='{case}'").specH2TranspCost.iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=epd_samp,
                    y=[y for _ in epd_samp],
                    mode='lines',
                    name=case,
                    line=dict(color=self._config['line_colour'][case], width=self._config['global']['lw_default']),
                    showlegend=False,
                ),
                row=2,
                col=c + 1,
            )

            thisData = costDataComm.query(f"case=='{case}'")
            fig.add_trace(
                go.Scatter(
                    x=thisData.epdiff,
                    y=len(thisData) * [y],
                    mode='markers',
                    text=thisData.case,
                    name=case,
                    legendgroup=case,
                    showlegend=False,
                    marker=dict(
                        color=self._config['line_colour'][case],
                        symbol=self._config['symbol'],
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color=self._config['line_colour'][case],
                    ),
                    line_width=self._config['global']['lw_thin'],
                    line_color=self._config['line_colour'][case],
                ),
                row=2,
                col=c + 1,
            )
