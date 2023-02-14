import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.helperFuncs import groupbySumval
from src.scaffolding.plotting.AbstractPlot import AbstractPlot


class SensitivityPlot(AbstractPlot):
    def _prepare(self):
        if self.anyRequired('fig6'):
            self._prep = self.__makePrep(
                self._finalData['costData'],
                self._finalData['costDataRef'],
                self._finalData['prices'],
                self._finalData['costH2Transp'],
            )


    # make adjustments to data
    def __makePrep(self, costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, costH2TranspParams: pd.DataFrame):
        # electricity price difference from prices object
        elecPriceDiff = prices \
            .query("component=='electricity' and location=='importer'").filter(['period', 'val']) \
            .merge(prices.query("component=='electricity' and location=='exporter'").filter(['period', 'val']), on=['period']) \
            .assign(priceDiff=lambda x: x.val_x - x.val_y) \
            .drop(columns=['val_x', 'val_y'])


        # transportation cost for hydrogen
        costH2Transp = groupbySumval(costData.query("type=='transport' and component=='hydrogen'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case']) \
            .rename(columns={'val': 'costH2Transp'})


        # cost delta of Cases 1-3 in relation to Base Case without H2 transport cost
        cost = groupbySumval(costData, ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

        costDelta = cost.query("case.notnull() & case!='Base Case'") \
            .merge(cost.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
            .assign(cost=lambda x: x.val_y - x.val_x) \
            .drop(columns=['val_x', 'val_y', 'baseRoute'])


        # cost delta of Cases 1-3 in relation to Base Case without H2 transport cost for reference with zero elec price difference
        costRef = groupbySumval(costDataRef, ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

        costRefDelta = costRef.query("case.notnull() & case!='Base Case'") \
            .merge(costRef.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
            .assign(costRef=lambda x: x.val_y - x.val_x) \
            .drop(columns=['val_x', 'val_y', 'baseRoute'])


        # base H2 transportation cost
        costH2TranspBase = costH2TranspParams \
            .filter(['mode', 'val', 'period']) \
            .rename(columns={'val': 'costH2TranspBase', 'mode': 'case'}) \
            .replace({'case': {'shipping': 'Case 1A', 'pipeline': 'Case 1B'}})


        # linear interpolation of cost difference as a function of elec price
        merge = costRefDelta \
            .merge(costDelta, on=['commodity', 'route', 'case', 'period']) \
            .merge(costH2Transp, on=['commodity', 'route', 'case', 'period'], how='left') \
            .merge(costH2TranspBase, on=['period', 'case'], how='left') \
            .merge(elecPriceDiff, on=['period'])

        pd_samples = np.linspace(self._config['xrange'][0], self._config['xrange'][1], self._config['samples'])
        tc_samples = np.linspace(self._config['bottom']['yrange'][0], self._config['bottom']['yrange'][1], self._config['samples'])
        pd, tc = np.meshgrid(pd_samples, tc_samples)

        commodities = costDelta.commodity.unique().tolist()
        cases = costDelta.case.unique()

        plotData = {
            'top': {comm: {case: {} for case in cases} for comm in commodities},
            'bottom': {comm: {} for comm in commodities},
        }
        for comm in commodities:
            for case in cases:
                r = merge.query(f"commodity=='{comm}' & case=='{case}' & period=={self._config['showYear']}").iloc[0]

                plotData['top'][comm][case] = r.costRef + (r.cost - r.costRef) / r.priceDiff * pd_samples

                if case == 'Case 1A':
                    plotData['bottom'][comm] = r.costRef + (r.cost - r.costRef) / r.priceDiff * pd - (
                                r.costH2Transp / r.costH2TranspBase * tc - r.costH2Transp)


        # benchmark cost
        benchmarkCost = cost.query("case=='Base Case'")


        # default price difference
        defaultPriceDiff = elecPriceDiff.query(f"period=={self._config['showYear']}").iloc[0].priceDiff


        return {
            'pd_samples': pd_samples,
            'tc_samples': tc_samples,
            'plotData': plotData,
            'defaultPriceDiff': defaultPriceDiff,
            'benchmarkCost': benchmarkCost,
            'costH2TranspBase': costH2TranspBase,
        }


    def _plot(self):
        # make fig5
        if self.anyRequired('fig6'):
            self._ret['fig6'] = self.__makePlot(**self._prep)


    def __makePlot(self, pd_samples: np.ndarray, tc_samples: np.ndarray, plotData: dict, defaultPriceDiff: float,
                   benchmarkCost: pd.DataFrame, costH2TranspBase: pd.DataFrame):
        commodities = [c for c in plotData['top']]


        # create figure
        fig = make_subplots(
            rows=2,
            cols=len(commodities),
            # shared_yaxes=True,
            horizontal_spacing=0.025,
            vertical_spacing=0.08,
            specs=[len(commodities) * [{"secondary_y": True}], len(commodities) * [{}]],
        )


        # plot heatmaps and contours
        for i, commodity in enumerate(commodities):
            self.__addTop(i, commodity, fig, pd_samples, plotData['top'][commodity])

            self.__addBottom(i, commodity, fig, pd_samples, tc_samples, plotData['bottom'][commodity])


            # add top to bottom
            for case in ['Case 1A', 'Case 1B']:
                y = costH2TranspBase.query(f"case=='{case}' & period=={self._config['showYear']}").costH2TranspBase.iloc[0]
                fig.add_trace(
                    go.Scatter(
                        x=pd_samples,
                        y=[y for _ in pd_samples],
                        mode='lines',
                        name=case,
                        line=dict(color=self._config['line_colour'][case], width=self._config['global']['lw_default']),
                        showlegend=False,
                    ),
                    row=2,
                    col=i+1,
                )


            # add vertical line indicating default price assumption
            fig.add_vline(
                defaultPriceDiff,
                row=1,
                col=i+1,
                line_dash='dash',
            )
            fig.add_vline(
                defaultPriceDiff,
                row=2,
                col=i+1,
                line_dash='dash',
            )


        # set axes labels and ranges
        baseCaseCost = benchmarkCost.query(f"commodity=='{commodity}' and period=={self._config['showYear']}").iloc[0].val

        fig.update_layout(
            legend_title='',

            **{
                f"xaxis{i+1 if i else ''}": dict(range=self._config['xrange'], showticklabels=False)
                for i, commodity in enumerate(commodities)
            },
            **{
                f"yaxis{2*i+1 if i else ''}": dict(range=[0.0, self._config['top']['ymax']], showticklabels=False)
                for i, commodity in enumerate(commodities)
            },
            **{
                f"yaxis{2*i+2}": dict(range=[0.0, self._config['top']['ymax'] / baseCaseCost * 100], showticklabels=False)
                for i, commodity in enumerate(commodities)
            },

            **{
                f"xaxis{i+4}": dict(range=self._config['xrange'])
                for i, commodity in enumerate(commodities)
            },
            **{
                f"yaxis{i+7}": dict(range=self._config['bottom']['yrange'], showticklabels=False)
                for i, commodity in enumerate(commodities)
            },
        )
        fig.update_layout(
            xaxis5_title=f"{self._config['xaxislabel']}",
            yaxis=dict(title=self._config['top']['yaxislabel'], showticklabels=True),
            yaxis6=dict(title=self._config['top']['yaxis2label'], showticklabels=True),
            yaxis7=dict(title=self._config['bottom']['yaxislabel'], showticklabels=True),
        )


        return fig


    def __addTop(self, i: int, commodity: str, fig, pd_samples, plotData: dict):
        for case, caseData in plotData.items():
            if case == 'Case 1A':
                continue

            fig.add_trace(
                go.Scatter(
                    x=pd_samples,
                    y=caseData,
                    mode='lines',
                    name=case,
                    line=dict(color=self._config['line_colour'][case], width=self._config['global']['lw_default']),
                    showlegend=not i,
                    hovertemplate=f"<b>{case}</b><br>{self._config['xlabelshort']}: %{{x:.2f}}<br>{self._config['bottom']['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                row=1,
                col=i + 1,
            )

        # add text annotations explaining figure content
        fig.add_annotation(
            x=0.0,
            xref='x domain',
            xanchor='left',
            y=1.0,
            yref='y domain',
            yanchor='top',
            text=f"<b>{commodity}</b>",
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=3,
            bgcolor='white',
            row=1,
            col=i + 1,
        )

        # add second yaxis
        fig.add_trace(
            go.Scatter(x=self._config["xrange"], y=[-10, -10], showlegend=False),
            secondary_y=True,
            row=1,
            col=i + 1,
        )


    def __addBottom(self, i: int, commodity: str, fig, pd_samples, tc_samples, plotData: dict):
        fig.add_trace(
            go.Heatmap(
                x=pd_samples,
                y=tc_samples,
                z=plotData,
                zsmooth='best',
                zmin=self._config['zrange'][0],
                zmax=self._config['zrange'][1],
                colorscale=[
                    [0.0, self._config['zcolours'][0]],
                    [1.0, self._config['zcolours'][1]],
                ],
                colorbar=dict(
                    x=1.01,
                    y=(0.5-0.05)/2,
                    yanchor='middle',
                    len=(0.5-0.025/2),
                    title=self._config['zaxislabel'],
                    titleside='right',
                    tickvals=[float(t) for t in self._config['zticks']],
                    ticktext=self._config['zticks'],
                ),
                showscale=True,
                hoverinfo='skip',
            ),
            row=2,
            col=i + 1,
        )

        fig.add_trace(
            go.Contour(
                x=pd_samples,
                y=tc_samples,
                z=plotData,
                contours_coloring='lines',
                colorscale=[
                    [0.0, '#000000'],
                    [1.0, '#000000'],
                ],
                line_width=self._config['global']['lw_thin'],
                contours=dict(
                    showlabels=True,
                    start=self._config['zrange2'][0],
                    end=self._config['zrange2'][1],
                    size=self._config['zdelta'][i],
                ),
                showscale=False,
                hoverinfo='skip',
            ),
            row=2,
            col=i + 1,
        )

        # add text annotations explaining figure content
        fig.add_annotation(
            x=0.0,
            xref='x domain',
            xanchor='left',
            y=1.0,
            yref='y domain',
            yanchor='top',
            text=f"<b>{commodity}</b>",
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=3,
            bgcolor='white',
            row=2,
            col=i + 1,
        )
