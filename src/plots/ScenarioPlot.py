import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from posted.calc_routines.LCOX import LCOX

from src.utils import load_yaml_config_file, load_yaml_plot_config_file
from src.plots.BasePlot import BasePlot


class ScenarioPlot(BasePlot):
    figs, cfg = load_yaml_plot_config_file('ScenarioPlot')

    def plot(self, inputs: dict, outputs: dict, subfig_names: list) -> dict:
        plot_data = self._prepare(inputs, outputs)
        plot_data['scenario_name'] = plot_data['scenario'].map(self.cfg['scenario_names'])

        fig = px.bar(
            plot_data,
            x='scenario_name',
            y='value',
            color='commodity',
            facet_col='epdcase',
            color_discrete_sequence=list(self._glob_cfg['commodity_colours'].values()),
            text_auto=True,
        )

        # add legend group
        for trace in fig.data:
            trace['legendgroup'] = 'protection'
            trace['legendgrouptitle_text'] = f"<b>{self.cfg['legendgroup_titles']['protection']}</b>"

        # add federal budget data
        budget_data = pd.DataFrame.from_dict(self.cfg['planned_expenses'], orient='index')

        for t in budget_data['type'].unique():
            this_data = budget_data.query(f"type=='{t}'")

            fig.add_trace(
                go.Bar(
                    x=this_data['label'],
                    y=this_data['value'],
                    marker_color=self.cfg['expenses_color'][t],
                    name=t,
                    xaxis='x4',
                    yaxis='y4',
                    legendgroup='existing',
                    legendgrouptitle_text=f"<b>{self.cfg['legendgroup_titles']['existing']}</b>",
                )
            )

        # adjust axes domains
        n = 3
        xspace = 0.67
        xdelta = 0.02
        xranges = list(zip(np.linspace(0, xspace+xdelta, n+1)[:n], np.linspace(-xdelta, xspace, n+1)[1:]))
        fig.update_layout(
            **{
                f"xaxis{i+1 if i else ''}": dict(
                    domain=xranges[i],
                )
                for i in range(n)
            },
            xaxis4={'domain': [xspace+xdelta, 1.0]},
            yaxis4={'anchor': 'x4', 'matches': 'y', 'side': 'right'},
        )

        # update text template
        for trace in fig.data:
            trace['texttemplate'] = '%{y:.1f} bn EUR/a'
            trace['hoverinfo'] = 'skip'

        # adjust legend and axes titles
        fig.update_layout(
            legend=dict(
                title='',
                xanchor='left',
                yanchor='top',
                x=0.005,
                y=0.99,
            ),
            **{f"xaxis{i+1 if i else ''}_title": '' for i in range(n+1)},
            yaxis_title=self.cfg['yaxis_title']['left'],
            yaxis4_title=self.cfg['yaxis_title']['right'],
            **{f"yaxis{i + 1 if i else ''}_range": [0.0, self.cfg['yaxis_max']] for i in range(n + 1)},
            # yaxis4_tickmode='array',
            # yaxis4_tickvals=[],
            yaxis4_ticklabelposition='outside right',
            hovermode=False,
        )

        # replace annotations
        fig.layout.annotations = []
        for s, scen in enumerate(self.cfg['epdcases'] + ['For comparison']):
            self._add_annotation(fig, scen.capitalize(), s)

        return {'fig6': fig}


    def _prepare(self, inputs: dict, outputs: dict):
        # produce LCOX DataTable by assuming final elec prices and applying calc routine, then combine into single
        # dataframe for all commodities/value chains
        lcox = []
        for comm in inputs['value_chains']:
            lcox_comm = outputs['tables'][comm] \
                .assume(outputs['cases'][comm]) \
                .calc(LCOX) \
                .data['LCOX'] \
                .query(f"epdcase.isin({self.cfg['epdcases']})") \
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
            lcox.append(lcox_comm)
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
                for epdcase in self.cfg['epdcases']
                for scenario in scenarios.index.unique('scenario')
            ]] \
            .reset_index()
