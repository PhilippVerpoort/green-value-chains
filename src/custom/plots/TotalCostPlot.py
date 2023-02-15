import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import all_routes


class TotalCostPlot(BasePlot):
    _complete = True

    def _prepare(self):
        if self.anyRequired('fig3'):
            self._prep = self.__makePrep(self._finalData['costData'])


    # make adjustments to data (route names, component labels)
    def __makePrep(self, costData: pd.DataFrame):
        showRoutes = costData['route'].unique()
        showYears = costData['period'].unique()

        # remove upstream cost entries
        costDataNew = costData.copy().query(f"type!='upstream'")

        # define route names and ordering
        route_names_woimp = {route_id: route_vals['name'] for route_details in all_routes.values() for route_id, route_vals in sorted(route_details.items()) if route_id in costDataNew['route'].unique()}
        route_names_wiimp = {route_id: route_id.split('--')[-1] for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
        route_names = {**route_names_woimp, **route_names_wiimp}

        # rename routes into something readable
        costDataNew.replace({'route': route_names}, inplace=True)

        # aggregate
        costDataNew = self._groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['period', 'commodity', 'route'], keep=['case'])

        # sort by commodities
        commodityOrder = costData.commodity.unique().tolist()
        costDataNew.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)

        # add relative data
        costDataNewBase = self._groupbySumval(costDataNew.query(f"case=='Base Case'"), ['period', 'commodity'])
        costDataNew = costDataNew \
            .merge(costDataNewBase, on=['period', 'commodity']) \
            .assign(val=lambda x: x.val_x, val_rel=lambda x: x.val_x / x.val_y) \
            .drop(columns=['val_x', 'val_y'])


        # replace
        costDataNew = costDataNew \
            .replace({'route': 'Case 1A'}, 'Case 1A/B') \
            .replace({'route': 'Case 1B'}, 'Case 1A/B')


        return {
            'costData': costDataNew
        }


    def _plot(self):
        # produce fig3
        if self.anyRequired('fig3'):
            self._ret['fig3'] = self.__makePlot(**self._prep)

        return self._ret


    def __makePlot(self, costData: pd.DataFrame):
        q = f"period=={self._config['show_year']} & case.notnull()"
        costData = costData.query(q)
        commodities = costData.commodity.unique()


        # create figure
        fig = make_subplots(
            cols=len(commodities),
            rows=2,
            horizontal_spacing=0.05,
        )


        # loop over commodities (three columns)
        for i, comm in enumerate(costData.commodity.unique()):
            costDataComm = costData\
                .query(f"commodity=='{comm}'") \
                .sort_values(by='route')

            # add top plots
            self.__addTop(fig, i, comm, costDataComm)

            # add annotations
            self._addAnnotationComm(fig, i, comm)

            # add axis layout
            self._updateAxisLayout(
                fig, i,
                xaxis=dict(categoryorder='category ascending'),
                yaxis=dict(title=self._config['yaxislabel'], range=self._config['yrange']),
            )


        # update layout
        fig.update_layout(
            barmode='stack',
            legend_title='',
        )


        return fig


    def __addTop(self, fig, i, comm, costDataComm):
        costDataComm = costDataComm.query(f"case!='Case 1A'")

        fig.add_trace(
            go.Scatter(
                x=costDataComm.route,
                y=100.0 * costDataComm.val_rel,
                name=comm,
                marker=dict(
                    color=self._config['colour'][comm],
                    symbol=self._config['symbol'],
                    size=self._config['global']['marker_def'],
                    line_width=self._config['global']['lw_thin'],
                    line_color=self._config['colour'][comm],
                ),
                line=dict(
                    shape='spline',
                    # width=0.0 if not i else None,
                    dash='dash' if not i else 'solid',
                ),
                showlegend=True,
            ),
            row=1,
            col=i + 1,
        )
