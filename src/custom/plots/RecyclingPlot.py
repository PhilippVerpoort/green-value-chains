import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_data import commodities


class RecyclingPlot(BasePlot):
    _complete = True

    def _decorate(self):
        super(RecyclingPlot, self)._decorate()

        # loop over commodities (three columns)
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for fig in self._ret.values():
                self._addAnnotationComm(fig, c, comm)


    def _prepare(self):
        if self.anyRequired('figS4'):
            self._prep = self.__makePrep(
                self._finalData['costData'],
                self._finalData['costDataRec'],
            )


    # make adjustments to data
    def __makePrep(self, costData: pd.DataFrame, costDataRec: pd.DataFrame):
        shares = [{'commodity': 'Steel', 'sh': 0.1}, {'commodity': 'Urea', 'sh': 0.0}, {'commodity': 'Ethylene', 'sh': 0.0}]
        sharesRec = [{'commodity': 'Steel', 'shRef': 0.85}, {'commodity': 'Urea', 'shRef': 1.0}, {'commodity': 'Ethylene', 'shRef': 1.0}]

        # cost delta of Cases 1-3 in relation to Base Case
        cost = self._groupbySumval(costData, ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

        costDelta = cost.query("case.notnull() & case!='Base Case'") \
            .merge(cost.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
            .assign(cost=lambda x: x.val_y - x.val_x) \
            .merge(pd.DataFrame.from_records(shares)) \
            .drop(columns=['val_x', 'val_y', 'baseRoute', 'route'])


        # cost delta of Cases 1-3 in relation to Base Case for reference with recycling
        costRec = self._groupbySumval(costDataRec, ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

        costRecDelta = costRec.query("case.notnull() & case!='Base Case'") \
            .merge(costRec.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
            .assign(costRef=lambda x: x.val_y - x.val_x) \
            .merge(pd.DataFrame.from_records(sharesRec)) \
            .drop(columns=['val_x', 'val_y', 'baseRoute', 'route'])


        # linear interpolation of cost difference as a function of elec price
        tmp = costRecDelta.merge(costDelta, on=['commodity', 'case', 'period'])

        plotData = pd.concat([
            #tmp.assign(cd=lambda r: r.costRef + ((r.cost-r.costRef)/(r.sh-r.shRef)) * share, share=share)
            tmp.assign(cd=lambda r: r.cost + (r.costRef - r.cost) * (share - r.sh) / (r.shRef - r.sh), share=share)
            for share in np.linspace(self._config['xrange'][0], self._config['xrange'][1], self._config['xsamples'])
        ]).drop(columns=['cost', 'costRef', 'shRef'])


        return {
            'plotData': plotData,
        }


    def _plot(self):
        # make fig5
        if self.anyRequired('figS4'):
            self._ret['figS4'] = self.__makePlot(**self._prep)


    def __makePlot(self, plotData: dict):
        # create figure
        fig = make_subplots(
            cols=len(commodities),
            shared_yaxes=True,
            horizontal_spacing=0.025,
        )


        # plot lines
        for i, comm in enumerate(commodities):
            commData = plotData.query(f"commodity=='{comm}'")

            for j, year in enumerate(plotData.period.unique()):
                yearData = commData.query(f"period=={year}")

                for case in plotData.case.unique():
                    thisData = yearData.query(f"case=='{case}'")

                    if case == 'Case 1A':
                        continue

                    fig.add_trace(
                        go.Scatter(
                            x=thisData.share*100,
                            y=thisData.cd,
                            mode='lines',
                            name=int(year),
                            legendgroup=case,
                            legendgrouptitle=dict(text=f"<b>{case}</b>"),
                            line=dict(color=self._config['line_colour'][case], width=self._config['global']['lw_default'], dash='dot' if j else None),
                            showlegend=not i,
                            hovertemplate=f"<b>{case} in {int(year)}</b><br>Price difference: %{{x:.2f}}<br>Cost difference: %{{y:.2f}}<extra></extra>",
                        ),
                        col=i+1,
                        row=1,
                    )


        # set axes labels
        fig.update_layout(
            legend_title='',
            yaxis=dict(title=self._config['yaxislabel'], range=[0.0, self._config['ymax']]),
            **{
                f"xaxis{i+1 if i else ''}": dict(title=f"{self._config['xaxislabel']}", range=self._config['xrange'])
                for i, commodity in enumerate(commodities)
            }
        )


        return fig
