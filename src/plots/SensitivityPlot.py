from string import ascii_lowercase

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from posted.calc_routines.LCOX import LCOX

from src.utils import loadYAMLConfigFile
from src.plots.BasePlot import BasePlot


class SensitivityPlot(BasePlot):
    figs = loadYAMLConfigFile(f"figures/SensitivityPlot")
    _addSubfigName = True
    _addSubfigNameDict = {b: ascii_lowercase[a] for a, b in enumerate([0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13])}

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        super(SensitivityPlot, self)._decorate(inputs, outputs, subfigs)

        # loop over commodities (three columns)
        commodities = list(inputs['value_chains'].keys())
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for subfigPlot in subfigs.values():
                self._addAnnotationComm(subfigPlot, comm, c)

    def plot(self, inputs: dict, outputs: dict, subfigNames: list) -> dict:
        cfg = self._figCfgs['fig7']
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
            commData = self.__prepareData(inputs, outputs, comm, cfg)

            # add rows
            for row, senstype in enumerate(cfg['senstypes']):
                if (senstype == 'dachp' and comm == 'Steel') or \
                   (senstype == 'repurpose' and comm == 'Ethylene'):
                    continue

                commDataRow = commData.query(f"senstype=='{senstype}'")
                self.__addRow(fig, c, comm, row, commDataRow, cfg, h2transp=(senstype == 'h2transp'))

                # add zeroline top
                fig.add_hline(100.0, row=row+1, col=c+1, line_color='black')

                # update top axes layout
                self._updateAxisLayout(
                    fig, c+3*row,
                    xaxis=dict(
                        range=[-0.1, +3.65],
                        tickmode='array',
                        tickvals=[],
                    ),
                    yaxis=dict(
                        showticklabels=not c,
                        **cfg['yaxis'],
                    ),
                )

            # update top axes layout
            self._updateAxisLayout(
                fig, c+3*row,
                xaxis=dict(
                    categoryorder='category ascending',
                    range=[-0.1, +3.65],
                    tickmode='array',
                    tickvals=[i for i in range(commData['impcase'].nunique())],
                    ticktext=[d for d in commData['impcase_display'].unique()],
                ),
            )

        # label
        for row, senstype in enumerate(cfg['senstypes']):
            fig.add_annotation(
                showarrow=False,
                text=cfg['senstypes'][senstype]['label'],
                textangle=-90,
                x=1.015,
                xref=f"paper",
                xanchor='left',
                y=0.5,
                yref=f"y{2+3*row} domain",
                yanchor='middle',
                bordercolor='black',
                borderwidth=self._globCfg['globStyle'][self._target]['lw_thin'],
                borderpad=10*self._globCfg['globStyle'][self._target]['lw_thin'],
                bgcolor='white',
                opacity=1.0,
            )

        # add dummy data for legend
        self.__addDummyLegend(fig, cfg)

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
            yaxis7_title=cfg['yaxis_title'],
        )

        return {'fig7': fig}

    def __addDummyLegend(self, fig: go.Figure, cfg: dict):
        for legend, symbol in [('Case 1A', cfg['symbolCase1A']), ('Other<br>cases', cfg['symbol'])]:
            fig.add_trace(
                go.Scatter(
                    x=[-1000.0],
                    y=[-1000.0],
                    name=legend,
                    mode='markers+lines',
                    marker=dict(
                        color='black',
                        symbol=symbol,
                        size=cfg['globStyle'][self._target]['marker_sm'],
                        line_width=cfg['globStyle'][self._target]['lw_thin'],
                        line_color='black',
                    ),
                    showlegend=True,
                    legendgroup='dummy',
                ),
                row=1,
                col=1,
            )

    def __prepareData(self, inputs: dict, outputs: dict, comm: str, cfg: dict):
        # prepare base data
        epd = outputs['cases'][comm].query(f"epdcase=='{cfg['epdcase']}'").droplevel('epdcase')
        table = outputs['tables'][comm] \
            .assume(epd)

        sensitivities = []

        # sensitivity 1 -- wacc
        tmp = outputs['procLocs'][comm].replace('RE-scarce', inputs['other_assump']['irate']['RE-scarce'])
        assumpWACC = pd.concat([
                tmp.replace('RE-rich', wacc).assign(sensvar=f"{wacc}%").set_index('sensvar', append=True)
                for wacc in [5.0, 8.0, 12.0, 20.0]
            ]) \
            .astype(float) \
            .apply(lambda x: x/100.0) \
            .assign(type='wacc') \
            .set_index('type', append=True) \
            .unstack('type')
        sensitivities.append(
                table \
                    .assume(assumpWACC) \
                    .calc(LCOX) \
                    .data['LCOX']
                    .assign(senstype='wacc') \
                    .set_index('senstype', append=True)
            )

        # sensitivity 2 -- capex
        assumpCAPEX = pd.concat([
                table.data['value', 'capex'] \
                    .apply(lambda x: x * (1.0 + sensvar/100))
                    .assign(sensvar=f"{sensvar:+d}%") \
                    .set_index(['sensvar'], append=True)
                for sensvar in [-50, 0, +50, +100]
            ]) \
            .assign(type='capex') \
            .set_index('type', append=True) \
            .unstack('type')
        sensitivities.append(
            table \
                .assume(assumpCAPEX) \
                .calc(LCOX) \
                .data['LCOX'] \
                .assign(senstype='capex') \
                .set_index('senstype', append=True)
        )

        # sensitivity 3 -- h2 transp cost
        assumpH2TranspCost = pd.concat([
                table.data['assump', 'transp:h2'] \
                    .apply(lambda x: pd.Series(index=x.index, data=(sensvar if (x == x).all() else np.nan)), axis=1) \
                    .assign(sensvar=f"{sensvar} EUR/MWh") \
                    .set_index(['sensvar'], append=True)
                for sensvar in [5, 15, 35, 50, 70, 90]
            ]) \
            .astype('pint[EUR/MWh]') \
            .assign(type='transp:h2') \
            .set_index('type', append=True) \
            .unstack('type')
        sensitivities.append(
            table \
                .assume(assumpH2TranspCost) \
                .calc(LCOX) \
                .data['LCOX'] \
                .assign(senstype='h2transp') \
                .set_index('senstype', append=True) \
                .query(f"impsubcase!='Case 1A'")
        )

        # sensitivity 4 -- DAC energy demand
        if comm != 'Steel':
            sensitivities.append(
                pd.concat([
                        table \
                            .calc(LCOX) \
                            .data['LCOX'] \
                            .assign(sensvar='w/ HP') \
                            .set_index('sensvar', append=True),
                        table \
                            .assume(
                            table.data['value'][[c for c in table.data['value'] if c[1] == 'HEATPUMP-4-DAC']] * np.nan) \
                            .assume(table.data[[('value', 'demand_sc:heat', 'DAC')]].rename(
                            columns={'demand_sc:heat': 'demand:heat'}).droplevel(level='part', axis=1)) \
                            .calc(LCOX) \
                            .data['LCOX'] \
                            .assign(sensvar='w/o HP') \
                            .set_index('sensvar', append=True),
                    ]) \
                    .assign(senstype='dachp') \
                    .set_index('senstype', append=True)
            )

        # sensitivity 5 -- repurposing
        if comm != 'Etyhlene':
            repurpProc = ['HOTROLL', 'HBNH3-ASU', 'UREA-SYN']
            originCAPEX = table.data['value', 'capex'][[t for t in repurpProc if t in table.data['value', 'capex']]]
            modifier = outputs['procLocs'][comm].filter(repurpProc).apply(lambda col: col.map({'RE-scarce': np.nan, 'RE-rich': 1.0}))
            assumpRepurp = pd.concat([
                    originCAPEX \
                        .assign(sensvar='w/o repurposing'),
                    (originCAPEX * modifier) \
                        .assign(sensvar='w/ repurposing'),
                ]) \
                .set_index('sensvar', append=True) \
                .assign(type='capex') \
                .set_index('type', append=True) \
                .unstack('type')
            sensitivities.append(
                table \
                    .assume(assumpRepurp) \
                    .calc(LCOX) \
                    .data['LCOX'] \
                    .assign(senstype='repurpose') \
                    .set_index('senstype', append=True)
            )

        # data for top row: calculate differences to Base Case, then rename import cases (1 to 1A/B and add subtitles),
        # and finally merge epd numbers for epdcases for display in plot
        commDataTop = pd.concat([s.reorder_levels(['impcase', 'impsubcase', 'sensvar', 'senstype']) for s in sensitivities]) \
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
                impcase_display=lambda df: df['impcase'].map({
                caseName: f"<b>{caseName + ('A/B' if caseName == 'Case 1' else '')}</b>:<br>{caseDesc}"
                for caseName, caseDesc in self._globCfg['globPlot']['case_names'].items()}),
                impcase_x=lambda df: df['impcase'].astype('category').cat.codes,
            )

        return commDataTop

    # add stacked bars showing levelised cost components
    def __addRow(self, fig: go.Figure, c: int, comm: str, row: int, commData: pd.DataFrame, cfg: dict, h2transp: bool):
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
                    color=cfg['globPlot']['commodity_colours'][comm],
                    symbol=cfg['symbol'],
                    size=cfg['globStyle'][self._target]['marker_sm'],
                    line_width=cfg['globStyle'][self._target]['lw_thin'],
                    line_color=cfg['globPlot']['commodity_colours'][comm],
                ),
                showlegend=False,
                legendgroup=comm,
                hoverinfo='skip',
            ),
            row=row + 1,
            col=c + 1,
        )

        # lines
        for l, sensvar in enumerate(commData['sensvar'].unique()):
            thisData = commData.query(f"sensvar=='{sensvar}'")
            plotData = thisData.query(f"impsubcase!='Case 1A'").sort_values(by='impcase')

            if h2transp:
                plotDataH2Transp = plotData.query(f"impcase!='Case 3'") if l else plotData
                fig.add_trace(
                    go.Scatter(
                        x=plotDataH2Transp['impcase_x'],
                        y=plotDataH2Transp['LCOP_rel'],
                        name=comm,
                        mode='lines',
                        line=dict(
                            shape='spline',
                            color=cfg['globPlot']['commodity_colours'][comm],
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
                        x=plotData['impcase_x'],
                        y=plotData['LCOP_rel'],
                        name=comm,
                        mode='lines',
                        line=dict(
                            shape='spline',
                            color=cfg['globPlot']['commodity_colours'][comm],
                        ),
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='skip',
                    ),
                    row=row + 1,
                    col=c + 1,
                )

                plotData = thisData.query(f"impsubcase=='Case 1B'")
                fig.add_trace(
                    go.Scatter(
                        x=[0.0, 0.9],
                        y=plotData['LCOP_rel'],
                        name=comm,
                        mode='lines',
                        line=dict(
                            shape='spline',
                            color=cfg['globPlot']['commodity_colours'][comm],
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
            pointData = thisData.query(f"impcase!='Base Case'")
            for impsubcase in pointData['impsubcase'].unique():
                thisData = pointData.query(f"impsubcase=='{impsubcase}'")
                fig.add_trace(
                    go.Scatter(
                        x=thisData['impcase_x'] - (0.1 if impsubcase == 'Case 1A' else 0.0),
                        y=thisData['LCOP_rel'],
                        name=comm,
                        mode='markers+lines',
                        marker=dict(
                            color=cfg['globPlot']['commodity_colours'][comm],
                            symbol=cfg['symbolCase1A'] if impsubcase == 'Case 1A' else cfg['symbol'],
                            size=cfg['globStyle'][self._target]['marker_sm'],
                            line_width=cfg['globStyle'][self._target]['lw_thin'],
                            line_color=cfg['globPlot']['commodity_colours'][comm],
                        ),
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='text' if hover else 'skip',
                        hovertemplate='<b>%{customdata[0]}</b><br>Sensitivity: %{customdata[1]}<br>Rel. prod. cost: %{y}%<extra></extra>',
                        customdata=thisData[['impsubcase', 'sensvar']] if hover else None,
                    ),
                    row=row + 1,
                    col=c + 1,
                )

        # sensvar annotations
        dys = 10.0 if h2transp else 8.0
        sensVarLabel = commData.query(f"impcase=='Case 1'" if h2transp else f"impcase=='Case 3'") \
            .sort_values(by='LCOP_rel') \
            .reset_index(drop=True) \
            .assign(LCOP_label_pos=lambda df: df['LCOP_rel'].mean() + dys * (df.index - len(df)/2 + 0.5))
        fig.add_trace(
            go.Scatter(
                x=sensVarLabel['impcase_x'],
                y=sensVarLabel['LCOP_label_pos'],
                text=sensVarLabel['sensvar'],
                name=comm,
                mode='markers+text',
                textposition='middle right',
                textfont_size=self.getFontSize('fs_tn'),
                textfont_color=cfg['globPlot']['commodity_colours'][comm],
                marker_size=cfg['globStyle'][self._target]['marker_sm'],
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
            for impsubcase, sensVarCmd, x, pos in [('Case 1A', 'max', 0.9, 'middle left'), ('Case 1B', 'min', 1.0, 'bottom right')]:
                caseLabel = commData.query(f"impsubcase=='{impsubcase}' & sensvar==sensvar.{sensVarCmd}()")
                fig.add_trace(
                    go.Scatter(
                        x=[x],
                        y=caseLabel['LCOP_rel'],
                        text=caseLabel['impsubcase'],
                        name=comm,
                        mode='markers+text',
                        textposition=pos,
                        textfont_size=self.getFontSize('fs_sm'),
                        textfont_color=cfg['globPlot']['commodity_colours'][comm],
                        marker_size=cfg['globStyle'][self._target]['marker_sm'],
                        marker_color='rgba(0,0,0,0)',
                        showlegend=False,
                        legendgroup=comm,
                        hoverinfo='skip',
                    ),
                    row=row + 1,
                    col=c + 1,
                )
