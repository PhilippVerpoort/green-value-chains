from string import ascii_lowercase

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from posted.calc_routines.LCOX import LCOX

from src.utils import load_yaml_plot_config_file
from src.plots.BasePlot import BasePlot


class SensitivityPlot(BasePlot):
    figs, cfg = load_yaml_plot_config_file('SensitivityPlot')
    _add_subfig_name = True
    _add_subfig_name_dict = {b: ascii_lowercase[a] for a, b in enumerate([0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13])}

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        super(SensitivityPlot, self)._decorate(inputs, outputs, subfigs)

        # loop over commodities (three columns)
        commodities = list(inputs['value_chains'].keys())
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for subfig_plot in subfigs.values():
                self._add_annotation_comm(subfig_plot, comm, c)

    def plot(self, inputs: dict, outputs: dict, subfig_names: list) -> dict:
        commodities = list(inputs['value_chains'].keys())

        # create figure
        fig = make_subplots(
            rows=5,
            cols=len(commodities),
            horizontal_spacing=0.035,
            vertical_spacing=0.04,
        )

        # add bars for each subplot
        for c, comm in enumerate(commodities):
            comm_data = self._prepare_data(inputs, outputs, comm)

            # add rows
            for row, senstype in enumerate(self.cfg['senstypes']):
                if (senstype == 'dachp' and comm == 'Steel') or \
                   (senstype == 'repurpose' and comm == 'Ethylene'):
                    continue

                comm_data_row = comm_data.query(f"senstype=='{senstype}'")
                self._add_row(fig, c, comm, row, comm_data_row, h2transp=(senstype == 'h2transp'))

                # add zeroline top
                fig.add_hline(100.0, row=row+1, col=c+1, line_color='black')

                # update top axes layout
                self._update_axis_layout(
                    fig, c+3*row,
                    xaxis=dict(
                        range=[-0.1, +3.65],
                        tickmode='array',
                        tickvals=[],
                    ),
                    yaxis=dict(
                        showticklabels=not c,
                        **self.cfg['yaxis'],
                    ),
                )

            # update top axes layout
            self._update_axis_layout(
                fig, c+3*row,
                xaxis=dict(
                    categoryorder='category ascending',
                    range=[-0.1, +3.65],
                    tickmode='array',
                    tickvals=[i for i in range(comm_data['impcase'].nunique())],
                    ticktext=[d for d in comm_data['impcase_display'].unique()],
                ),
            )

        # label
        for row, senstype in enumerate(self.cfg['senstypes']):
            fig.add_annotation(
                showarrow=False,
                text=self.cfg['senstypes'][senstype]['label'],
                textangle=-90,
                x=1.015,
                xref=f"paper",
                xanchor='left',
                y=0.5,
                yref=f"y{2+3*row} domain",
                yanchor='middle',
                bordercolor='black',
                borderwidth=self._styles['lw_thin'],
                borderpad=10*self._styles['lw_thin'],
                bgcolor='white',
                opacity=1.0,
            )

        # add dummy data for legend
        self._add_dummy_legend(fig)

        # update layout
        fig.update_layout(
            showlegend=True,
            legend=dict(
                title='',
                x=1.01,
                xanchor='left',
                y=0.0,
                yanchor='top',
            ),
            yaxis7_title=self.cfg['yaxis_title'],
        )

        return {'fig6': fig}

    def _add_dummy_legend(self, fig: go.Figure):
        for legend, symbol in [('Case 1A', self.cfg['symbolCase1A']), ('Other<br>cases', self.cfg['symbol'])]:
            fig.add_trace(
                go.Scatter(
                    x=[-1000.0],
                    y=[-1000.0],
                    name=legend,
                    mode='markers+lines',
                    marker=dict(
                        color='black',
                        symbol=symbol,
                        size=self._styles['marker_sm'],
                        line_width=self._styles['lw_thin'],
                        line_color='black',
                    ),
                    showlegend=True,
                    legendgroup='dummy',
                ),
                row=1,
                col=1,
            )

    def _prepare_data(self, inputs: dict, outputs: dict, comm: str):
        # prepare base data
        epd = outputs['cases'][comm].query(f"epdcase=='{self.cfg['epdcase']}'").droplevel('epdcase')
        table = outputs['tables'][comm] \
            .assume(epd)

        sensitivities = []

        # sensitivity 1 -- wacc
        tmp = outputs['procLocs'][comm].replace('RE-scarce', inputs['other_assump']['irate']['RE-scarce'])
        assump_wacc = pd.concat([
                tmp.replace('RE-rich', wacc).assign(sensvar=f"{wacc}%").set_index('sensvar', append=True)
                for wacc in [5.0, 8.0, 12.0, 20.0]
            ]) \
            .astype(float) \
            .apply(lambda x: x/100.0) \
            .assign(type='wacc') \
            .set_index('type', append=True) \
            .unstack('type')
        sensitivities.append(
                table.assume(assump_wacc)
                    .calc(LCOX)
                    .data['LCOX']
                    .assign(senstype='wacc')
                    .set_index('senstype', append=True)
            )

        # sensitivity 2 -- capex
        assump_capex = pd.concat([
                table.data['value', 'capex']
                    .apply(lambda x: x * (1.0 + sensvar/100))
                    .assign(sensvar=f"{sensvar:+d}%")
                    .set_index(['sensvar'], append=True)
                for sensvar in [-50, 0, +50, +100]
            ]) \
            .assign(type='capex') \
            .set_index('type', append=True) \
            .unstack('type')
        sensitivities.append(
            table
                .assume(assump_capex)
                .calc(LCOX)
                .data['LCOX']
                .assign(senstype='capex')
                .set_index('senstype', append=True)
        )

        # sensitivity 3 -- h2 transp cost
        assump_h2transp_cost = pd.concat([
                table.data['assump', 'transp:h2']
                    .apply(lambda x: pd.Series(index=x.index, data=(sensvar if (x == x).all() else np.nan)), axis=1)
                    .assign(sensvar=f"{sensvar} EUR/MWh")
                    .set_index(['sensvar'], append=True)
                for sensvar in [5, 15, 35, 50, 70, 90]
            ]) \
            .astype('pint[EUR/MWh]') \
            .assign(type='transp:h2') \
            .set_index('type', append=True) \
            .unstack('type')
        sensitivities.append(
            table
                .assume(assump_h2transp_cost)
                .calc(LCOX)
                .data['LCOX']
                .assign(senstype='h2transp')
                .set_index('senstype', append=True)
                .query(f"impsubcase!='Case 1A'")
        )

        # sensitivity 4 -- DAC energy demand
        if comm != 'Steel':
            sensitivities.append(
                pd.concat([
                        table
                            .calc(LCOX)
                            .data['LCOX']
                            .assign(sensvar='w/ HP')
                            .set_index('sensvar', append=True),
                        table
                            .assume(table.data['value'][[c for c in table.data['value']
                                                         if c[1] == 'HEATPUMP-4-DAC']] * np.nan)
                            .assume(table.data[[('value', 'demand_sc:heat', 'DAC')]].rename(
                                    columns={'demand_sc:heat': 'demand:heat'}).droplevel(level='part', axis=1))
                            .calc(LCOX)
                            .data['LCOX']
                            .assign(sensvar='w/o HP')
                            .set_index('sensvar', append=True),
                    ])
                    .assign(senstype='dachp')
                    .set_index('senstype', append=True)
            )

        # sensitivity 5 -- repurposing
        if comm != 'Etyhlene':
            repurp_proc = ['HOTROLL', 'HBNH3-ASU', 'UREA-SYN']
            origin_capex = table.data['value', 'capex'][[t for t in repurp_proc if t in table.data['value', 'capex']]]
            modifier = outputs['procLocs'][comm] \
                .filter(repurp_proc) \
                .apply(lambda col: col.map({'RE-scarce': np.nan, 'RE-rich': 1.0}))
            assump_repurp = pd.concat([
                    origin_capex.assign(sensvar='w/o repurposing'),
                    (origin_capex * modifier).assign(sensvar='w/ repurposing'),
                ]) \
                .set_index('sensvar', append=True) \
                .assign(type='capex') \
                .set_index('type', append=True) \
                .unstack('type')
            sensitivities.append(
                table
                    .assume(assump_repurp)
                    .calc(LCOX)
                    .data['LCOX']
                    .assign(senstype='repurpose')
                    .set_index('senstype', append=True)
            )

        # data for top row: calculate differences to Base Case, then rename import cases (1 to 1A/B and add subtitles),
        # and finally merge epd numbers for epdcases for display in plot
        comm_data_top = pd.concat([
                s.reorder_levels(['impcase', 'impsubcase', 'sensvar', 'senstype'])
                for s in sensitivities
            ]) \
            .pint.dequantify().droplevel('unit', axis=1) \
            .stack(['process', 'type']) \
            .groupby(['impcase', 'impsubcase', 'sensvar', 'senstype']) \
            .agg(sum) \
            .unstack(['sensvar', 'senstype']) \
            .apply(lambda row: 100.0 * row/row[0]) \
            .stack(['sensvar', 'senstype']) \
            .to_frame('LCOP_rel') \
            .reset_index() \
            .assign(
                impcase_x=lambda df: df['impcase'].astype('category').cat.codes,
                impcase_display=lambda df: df['impcase'].map({
                    case_name: f"<b>{case_name + ('A/B' if case_name == 'Case 1' else '')}</b>:<br>{case_desc}"
                    for case_name, case_desc in self._glob_cfg['case_names'].items()
                }),
            )

        return comm_data_top

    # add stacked bars showing levelised cost components
    def _add_row(self, fig: go.Figure, c: int, comm: str, row: int, comm_data: pd.DataFrame, h2transp: bool):
        # prepare hover info
        hover = self._target == 'webapp'

        # point zero
        fig.add_trace(
            go.Scatter(
                x=[0.0],
                y=[100.0],
                name=comm,
                mode='markers',
                marker=dict(
                    color=self._glob_cfg['commodity_colours'][comm],
                    symbol=self.cfg['symbol'],
                    size=self._styles['marker_sm'],
                    line_width=self._styles['lw_thin'],
                    line_color=self._glob_cfg['commodity_colours'][comm],
                ),
                showlegend=False,
                legendgroup=comm,
                hoverinfo='skip',
            ),
            row=row + 1,
            col=c + 1,
        )

        # lines
        for s, sensvar in enumerate(comm_data['sensvar'].unique()):
            this_data = comm_data.query(f"sensvar=='{sensvar}'")
            plot_data = this_data.query(f"impsubcase!='Case 1A'").sort_values(by='impcase')

            if h2transp:
                plot_data_h2transp = plot_data.query(f"impcase!='Case 3'") if s else plot_data
                fig.add_trace(
                    go.Scatter(
                        x=plot_data_h2transp['impcase_x'],
                        y=plot_data_h2transp['LCOP_rel'],
                        name=comm,
                        mode='lines',
                        line=dict(
                            shape='spline',
                            color=self._glob_cfg['commodity_colours'][comm],
                        ),
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='skip',
                    ),
                    row=row + 1,
                    col=c + 1,
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=plot_data['impcase_x'],
                        y=plot_data['LCOP_rel'],
                        name=comm,
                        mode='lines',
                        line=dict(
                            shape='spline',
                            color=self._glob_cfg['commodity_colours'][comm],
                        ),
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='skip',
                    ),
                    row=row + 1,
                    col=c + 1,
                )

                plot_data = this_data.query(f"impsubcase=='Case 1B'")
                fig.add_trace(
                    go.Scatter(
                        x=[0.0, 0.9],
                        y=plot_data['LCOP_rel'],
                        name=comm,
                        mode='lines',
                        line=dict(
                            shape='spline',
                            color=self._glob_cfg['commodity_colours'][comm],
                            dash='dash',
                        ),
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='skip',
                    ),
                    row=row + 1,
                    col=c + 1,
                )

            # points
            point_data = this_data.query(f"impcase!='Base Case'")
            for impsubcase in point_data['impsubcase'].unique():
                this_data = point_data.query(f"impsubcase=='{impsubcase}'")
                fig.add_trace(
                    go.Scatter(
                        x=this_data['impcase_x'] - (0.1 if impsubcase == 'Case 1A' else 0.0),
                        y=this_data['LCOP_rel'],
                        name=comm,
                        mode='markers+lines',
                        marker=dict(
                            color=self._glob_cfg['commodity_colours'][comm],
                            symbol=self.cfg['symbolCase1A'] if impsubcase == 'Case 1A' else self.cfg['symbol'],
                            size=self._styles['marker_sm'],
                            line_width=self._styles['lw_thin'],
                            line_color=self._glob_cfg['commodity_colours'][comm],
                        ),
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='text' if hover else 'skip',
                        hovertemplate='<b>%{customdata[0]}</b><br>'
                                      'Sensitivity: %{customdata[1]}<br>'
                                      'Rel. prod. cost: %{y}%<extra></extra>',
                        customdata=this_data[['impsubcase', 'sensvar']] if hover else None,
                    ),
                    row=row + 1,
                    col=c + 1,
                )

        # sensvar annotations
        dys = 10.0 if h2transp else 8.0
        sens_var_label = comm_data.query(f"impcase=='Case 1'" if h2transp else f"impcase=='Case 3'") \
            .sort_values(by='LCOP_rel') \
            .reset_index(drop=True) \
            .assign(LCOP_label_pos=lambda df: df['LCOP_rel'].mean() + dys * (df.index - len(df)/2 + 0.5))
        fig.add_trace(
            go.Scatter(
                x=sens_var_label['impcase_x'],
                y=sens_var_label['LCOP_label_pos'],
                text=sens_var_label['sensvar'],
                name=comm,
                mode='markers+text',
                textposition='middle right',
                textfont_size=self.get_font_size('fs_tn'),
                textfont_color=self._glob_cfg['commodity_colours'][comm],
                marker_size=self._styles['marker_sm'],
                marker_color='rgba(0,0,0,0)',
                showlegend=False,
                legendgroup=comm,
                hoverinfo='skip',
            ),
            row=row + 1,
            col=c + 1,
        )

        # case annotation
        if not h2transp:
            for impsubcase, sens_var_cmd, x, pos in [('Case 1A', 'max', 0.9, 'middle left'),
                                                     ('Case 1B', 'min', 1.0, 'bottom right'),]:
                case_label = comm_data.query(f"impsubcase=='{impsubcase}' & sensvar==sensvar.{sens_var_cmd}()")
                fig.add_trace(
                    go.Scatter(
                        x=[x],
                        y=case_label['LCOP_rel'],
                        text=case_label['impsubcase'],
                        name=comm,
                        mode='markers+text',
                        textposition=pos,
                        textfont_size=self.get_font_size('fs_sm'),
                        textfont_color=self._glob_cfg['commodity_colours'][comm],
                        marker_size=self._styles['marker_sm'],
                        marker_color='rgba(0,0,0,0)',
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='skip',
                    ),
                    row=row + 1,
                    col=c + 1,
                )
