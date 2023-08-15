import pandas as pd
import plotly.express as px
from posted.calc_routines.LCOX import LCOX

from src.utils import loadYAMLConfigFile
from src.plots.BasePlot import BasePlot


class ScenarioPlot(BasePlot):
    figs = loadYAMLConfigFile(f"figures/ScenarioPlot")

    def plot(self, inputs: dict, outputs: dict, subfigNames: list) -> dict:
        cfg = self._figCfgs['fig6']

        plotData = self.__prepare(inputs, outputs, cfg)

        fig = px.bar(
            plotData,
            x='scenario',
            y='value',
            color='commodity',
            facet_col='epdcase',
            color_discrete_sequence=list(cfg['globPlot']['commodity_colours'].values()),
            text_auto=True,
        )

        # update text template
        for d in fig.data:
            d['texttemplate'] = '%{y:.1f} bn EUR/a'
            d['hoverinfo'] = 'skip'

        # replace annotations
        fig.layout.annotations = []
        for s, scen in enumerate(cfg['epdcases']):
            self._addAnnotation(fig, scen.capitalize(), s)

        fig.update_layout(
            legend=dict(
                title='',
                xanchor='right',
                yanchor='top',
                x=0.99,
                y=0.99,
            ),
            xaxis_title='',
            xaxis2_title='',
            xaxis3_title='',
            yaxis_title=cfg['yaxis_title'],
            hovermode=False,
        )

        return {'fig6': fig}

    def __prepare(self, inputs: dict, outputs: dict, cfg: dict):
        # produce LCOX DataTable by assuming final elec prices and applying calc routine, then combine into single
        # dataframe for all commodities/value chains
        lcox = []
        for comm in inputs['value_chains']:
            lcoxComm = outputs['tables'][comm] \
                .assume(outputs['cases'][comm]) \
                .calc(LCOX) \
                .data['LCOX'] \
                .query(f"epdcase.isin({cfg['epdcases']})") \
                .pint.dequantify().droplevel('unit', axis=1) \
                .stack(['process', 'type']).to_frame('LCOP') \
                .groupby(['impsubcase', 'epdcase']) \
                .agg({'LCOP': 'sum'}) \
                .assign(commodity=comm) \
                .set_index('commodity', append=True) \
                .unstack(['commodity', 'epdcase']) \
                .apply(lambda row: row-row[-1]) \
                .stack(['commodity', 'epdcase']) \
                .unstack('impsubcase') \
                .reorder_levels(['commodity', 'epdcase'])
            lcox.append(lcoxComm)
        lcox = pd.concat(lcox)

        # add scenario data
        scenarios = pd.concat([inputs['scenarios']], keys=['share'], axis=1)
        savings = lcox.merge(scenarios, left_index=True, right_index=True)
        savings = savings['LCOP'] * savings['share']

        # add volume data, sum up, sort, and return
        return savings \
            .apply(lambda col: col * inputs['volumes'] / 1.0E+3) \
            .sum(axis=1) \
            .to_frame('value') \
            .loc[[
                (comm, epdcase, scenario)
                for comm in inputs['value_chains']
                for epdcase in cfg['epdcases']
                for scenario in scenarios.index.unique('scenario')
            ]] \
            .reset_index()
