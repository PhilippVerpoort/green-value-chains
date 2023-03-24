import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_data import commodities


class FlexiblePlot(BasePlot):
    _complete = True

    def _decorate(self):
        super(FlexiblePlot, self)._decorate()

        # loop over commodities (three columns)
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for fig in self._ret.values():
                self._addAnnotationComm(fig, c, comm)


    def _prepare(self):
        if self.anyRequired('figS2'):
            self._prep = self.__makePrep(
                self._finalData['costData'],
                self._finalData['costDataRef'],
                self._finalData['prices'],
            )


    # make adjustments to data
    def __makePrep(self, costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame):
        # cost delta of Cases 1-3 in relation to Base Case
        cost = self._groupbySumval(costData.query("type!='capital'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

        costDelta = cost.query("case=='Case 3'") \
            .merge(cost.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
            .assign(cost=lambda x: x.val_y - x.val_x) \
            .drop(columns=['val_x', 'val_y', 'baseRoute'])


        # cost delta of Cases 1-3 in relation to Base Case for reference with zero elec price difference
        costRef = self._groupbySumval(costDataRef.query("type!='capital'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

        costRefDelta = costRef.query("case=='Case 3'") \
            .merge(costRef.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
            .assign(costRef=lambda x: x.val_y - x.val_x) \
            .drop(columns=['val_x', 'val_y', 'baseRoute'])


        # capital cost data
        costCap = self._groupbySumval(costData.query("type=='capital' & case=='Case 3'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case']) \
            .rename(columns={'val': 'costCap'})


        # electricity price difference from prices object
        elecPriceDiff = prices \
            .query("component=='electricity' and location=='importer'").filter(['period', 'val']) \
            .merge(prices.query("component=='electricity' and location=='exporter'").filter(['period', 'val']), on=['period']) \
            .assign(priceDiff=lambda x: x.val_x - x.val_y) \
            .drop(columns=['val_x', 'val_y'])


        # linear interpolation of cost difference as a function of elec price
        tmp = costRefDelta \
            .merge(costDelta, on=['commodity', 'route', 'case', 'period']) \
            .merge(costCap, on=['commodity', 'route', 'case', 'period']) \
            .merge(elecPriceDiff, on=['period'])

        pd_samples = np.linspace(self._config['xrange'][0], self._config['xrange'][1], self._config['samples'])
        ocf_samples = np.linspace(self._config['yrange'][0], self._config['yrange'][1], self._config['samples'])
        pd, ocf = np.meshgrid(pd_samples, ocf_samples)

        plotData = {c: 0.0 for c in costData.commodity.unique().tolist()}
        for index, r in tmp.iterrows():
            if r.period != self._config['select_period']: continue
            plotData[r.commodity] = r.costCap * (100.0/ocf - 1.0) + r.costRef + (r.cost - r.costRef) / r.priceDiff * pd


        return {
            'pd_samples': pd_samples,
            'ocf_samples': ocf_samples,
            'plotData': plotData,
        }


    def _plot(self):
        # make fig5
        if self.anyRequired('figS2'):
            self._ret['figS2'] = self.__makePlot(**self._prep)


    def __makePlot(self, pd_samples: np.ndarray, ocf_samples: np.ndarray, plotData: dict):
        # create figure
        fig = make_subplots(
            cols=len(commodities),
            shared_yaxes=True,
            horizontal_spacing=0.025,
        )


        # plot heatmaps and contours
        for i, comm in enumerate(commodities):
            tickvals = [100 * i for i in range(6)]
            ticktext = [str(v) for v in tickvals]

            fig.add_trace(
                go.Heatmap(
                    x=pd_samples,
                    y=ocf_samples,
                    z=plotData[comm],
                    zsmooth='best',
                    zmin=self._config['zrange'][0],
                    zmax=self._config['zrange'][1],
                    colorscale=[
                        [0.0, self._config['zcolours'][0]],
                        [1.0, self._config['zcolours'][1]],
                    ],
                    colorbar=dict(
                        x=1.02,
                        y=0.5,
                        len=1.0,
                        title='Cost difference (EUR/t)',
                        titleside='right',
                        tickvals=tickvals,
                        ticktext=ticktext,
                    ),
                    showscale=True,
                    hoverinfo='skip',
                ),
                col=i+1,
                row=1,
            )

            fig.add_trace(
                go.Contour(
                    x=pd_samples,
                    y=ocf_samples,
                    z=plotData[comm],
                    contours_coloring='lines',
                    colorscale=[
                        [0.0, '#000000'],
                        [1.0, '#000000'],
                    ],
                    line_width=self._config['global']['lw_thin'],
                    contours=dict(
                        showlabels=True,
                        start=self._config['zrange'][0],
                        end=self._config['zrange'][1],
                        size=self._config['zdelta'],
                    ),
                    showscale=False,
                    hoverinfo='skip',
                ),
                col=i+1,
                row=1,
            )


        # set axes labels
        fig.update_layout(
            legend_title='',
            yaxis=dict(title=self._config['yaxislabel'], range=self._config['yrange']),
            **{
                f"xaxis{i+1 if i else ''}": dict(range=self._config['xrange'])
                for i, commodity in enumerate(plotData)
            },
            xaxis2_title=self._config['xaxislabel'],
        )


        return fig
