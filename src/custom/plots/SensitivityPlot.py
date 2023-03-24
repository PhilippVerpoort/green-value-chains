import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.data.calc.calc_cost import calcFCR
from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_data import commodities


class SensitivityPlot(BasePlot):
    _complete = True

    __vspc = 0.08
    __nrows = 4

    def _decorate(self):
        super(SensitivityPlot, self)._decorate()

        # loop over commodities (three columns)
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for fig in self._ret.values():
                self._addAnnotationComm(fig, c, comm)


    def _prepare(self):
        if self.anyRequired('fig7'):
            self._prep = self.__makePrep(
                self._finalData['costData'],
                self._finalData['techCostH2Transp'],
            )


    # make adjustments to data
    def __makePrep(self, costData: pd.DataFrame, techCostH2Transp: pd.DataFrame):
        epdMainCases = ['strong', 'medium', 'weak']

        # remove upstream cost entries, drop non-case routes, select period, and drop period column
        costDataNew = costData \
            .query(f"type!='upstream' and case.notnull() and period=={self._config['select_period']}") \
            .drop(columns=['period']) \
            .reset_index(drop=True)

        # separate into components, multiply with electricity prices, and aggregate
        components = {
            'capital_exporter': "type=='capital' and location=='exporter'",
            'h2transp': "type=='transport' and component=='hydrogen'",
            'energy': "type=='energy'",
        }
        components['other'] = ' and '.join([f"not ({c})" for c in components.values()])
        costComponents = {}
        for c, q in components.items():
            costComp = costDataNew.query(q)
            if c != 'energy':
                costComponents[c] = self._groupbySumval(costComp, ['commodity', 'case'])
            else:
                costComp = self._finaliseCostData(costComp, epperiod=self._config['select_period'])
                costComponents[c] = self._groupbySumval(costComp, ['commodity', 'case', 'epdcase'], keep=['epdiff'])

        # create dataframe containing epdiffs
        epdcaseDiffs = costComponents['energy'][['epdcase', 'epdiff']].drop_duplicates().set_index('epdcase')['epdiff']

        # add default h2transp cost
        specH2TranspCost = techCostH2Transp \
            .query(f"period=={self._config['select_period']}") \
            .filter(['mode', 'val']) \
            .rename(columns={'val': 'specH2TranspCost', 'mode': 'case'}) \
            .replace({'case': {'shipping': 'Case 1A', 'pipeline': 'Case 1B'}})
        costComponents['h2transp'] = costComponents['h2transp'].merge(specH2TranspCost, on=['case'], how='left')

        # add default WACC
        costComponents['capital_exporter'] = costComponents['capital_exporter'].assign(irate=self._inputData['options']['irate']['exporter'])

        # merge data together
        mergedData = costComponents['other'].rename(columns={'val': 'val_other'}) \
            .merge(costComponents['h2transp'].rename(columns={'val': 'val_h2transp'}), on=['commodity', 'case'], how='left') \
            .merge(costComponents['capital_exporter'].rename(columns={'val': 'val_cap_exp'}), on=['commodity', 'case'], how='left') \
            .fillna(0.0)
        for epdcase in costComponents['energy']['epdcase'].unique():
            tmp = costComponents['energy'] \
                .query(f"epdcase=='{epdcase}'") \
                .drop(columns=['epdcase', 'epdiff']) \
                .rename(columns={'val': f"val_energy_{epdcase}"})
            mergedData = mergedData \
                .merge(tmp, on=['commodity', 'case']) \
                .assign(**{f"val_tot_{epdcase}": lambda r: r.val_other + r.val_h2transp + r.val_cap_exp + r[f"val_energy_{epdcase}"]})

        # add base case to other rows for reference
        mergedData = pd.merge(
            mergedData.query(f"case!='Base Case'"),
            mergedData.query(f"case=='Base Case'").filter(regex='^(commodity|val_)', axis=1),
            on='commodity',
            suffixes=('', '_base'),
        ).reset_index(drop=True)
        for key in [key for key in mergedData.keys() if key.startswith('val') and not key.endswith('_base')]:
            mergedData = mergedData.assign(**{f"{key}_diff": lambda r: r[key] - r[f"{key}_base"]})

        # gather some basic plot data
        plotData = {
            'sensitivity1': {
                'xrange': self._config['sensitivity1']['xrange'],
                'ydata': {comm: {} for comm in commodities},
            },
            'sensitivity2': {
                'xrange': self._config['sensitivity2']['xrange'],
                'ydata': {comm: {} for comm in commodities},
            },
            'sensitivity3': {
                'xrange': [epdcaseDiffs['zero'], epdcaseDiffs['max']],
                'ydata': {comm: {} for comm in commodities},
            },
            'sensitivity4': {
                'xrange': [epdcaseDiffs['zero'], epdcaseDiffs['max']],
                'yrange': self._config['sensitivity4']['yrange'],
                'zdata': {},
            },
        }

        # linspace plotting data
        for s, r in ([(s, 'xrange') for s in plotData] + [('sensitivity4', 'yrange')]):
            plotData[s][f"{r[0]}data"] = np.linspace(*plotData[s][r], self._config['samples'])

        # loop over commodities
        for comm in commodities:
            for case in mergedData.case.unique():
                r = mergedData.query(f"commodity=='{comm}' & case=='{case}'").iloc[0]

                # linear interpolation for row 1
                wacc_linspace = plotData['sensitivity1']['xdata']
                ltime = self._inputData['options']['ltime']
                plotData['sensitivity1']['ydata'][comm][case] = \
                    r.val_tot_medium_diff + (calcFCR(wacc_linspace/100.0, ltime) / calcFCR(r.irate/100.0, ltime) - 1.0) * r.val_cap_exp

                # linear interpolation for row 2
                if case in ['Case 1A']:
                    htc_linspace = plotData['sensitivity2']['xdata']
                    for epdcase, epdiff in epdcaseDiffs.items():
                        if epdcase not in epdMainCases: continue
                        plotData['sensitivity2']['ydata'][comm][epdcase] = \
                            r[f"val_tot_{epdcase}_diff"] + r.val_h2transp * (htc_linspace / r.specH2TranspCost - 1.0)

                # linear interpolation for row 3
                epd_linspace = plotData['sensitivity3']['xdata']
                plotData['sensitivity3']['ydata'][comm][case] = \
                    r.val_tot_zero_diff + (epd_linspace - epdcaseDiffs['zero']) / \
                        (epdcaseDiffs['max'] - epdcaseDiffs['zero']) * (r.val_tot_max_diff - r.val_tot_zero_diff)

                # linear interpolation for row 4
                if case in ['Case 1A']:
                    epd_mesh, htc_mesh = np.meshgrid(plotData['sensitivity4']['xdata'], plotData['sensitivity4']['ydata'])
                    plotData['sensitivity4']['zdata'][comm] = \
                        (r.val_tot_zero_diff + (r.val_tot_max_diff - r.val_tot_zero_diff) *
                        (epd_mesh - epdcaseDiffs['zero']) / (epdcaseDiffs['max'] - epdcaseDiffs['zero']) +
                        r.val_h2transp * (htc_mesh / r.specH2TranspCost - 1.0)) \
                        / ((r.val_tot_zero_base + (r.val_tot_max_base - r.val_tot_zero_base) *
                        (epd_mesh - epdcaseDiffs['zero']) / (epdcaseDiffs['max'] - epdcaseDiffs['zero']))) * 100.0

        return {
            'mergedData': mergedData,
            'plotData': plotData,
            'epdcaseDiffs': epdcaseDiffs[epdMainCases],
        }


    def _plot(self):
        # make fig7
        if self.anyRequired('fig7'):
            self._ret['fig7'] = self.__makePlot(**self._prep)


    def __makePlot(self, mergedData: pd.DataFrame, plotData: dict, epdcaseDiffs: pd.Series):
        # create figure
        fig = make_subplots(
            rows=self.__nrows,
            cols=len(commodities),
            # shared_yaxes=True,
            horizontal_spacing=0.035,
            vertical_spacing=self.__vspc,
            # specs=[len(commodities) * [{"secondary_y": True}], len(commodities) * [{}]],
        )

        # loop over commodities
        for c, comm in enumerate(commodities):
            mergedDataComm = mergedData \
                .query(f"commodity=='{comm}'") \
                .reset_index(drop=True)

            # add row 1
            xdata = plotData['sensitivity1']['xdata']
            ydata = plotData['sensitivity1']['ydata'][comm]
            self.__addRow1(fig, c, xdata, ydata, mergedDataComm, self._config['sensitivity1']['epdcase'])

            # update axes row 1
            yrange = [min(d.min() for d in plotData['sensitivity1']['ydata'][comm].values()),
                      max(d.max() for d in plotData['sensitivity1']['ydata'][comm].values())]
            yrange[1] += 0.1 * (yrange[1] - yrange[0])
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(range=plotData['sensitivity1']['xrange']),
                yaxis=dict(range=yrange),
            )

            # add annotation above subplot
            labelText = f"Elec.-price case {self._config['sensitivity1']['epdcase']} ({epdcaseDiffs[self._config['sensitivity1']['epdcase']]} EUR/MWh) only"
            self._addAnnotation(fig, c, labelText, row=1)

            # add row 2
            xdata = plotData['sensitivity2']['xdata']
            ydata = plotData['sensitivity2']['ydata'][comm]
            self.__addRow2(fig, c, xdata, ydata, mergedDataComm, epdcaseDiffs)

            # update axes row 2
            self._updateAxisLayout(
                fig, c+3,
                xaxis=dict(range=plotData['sensitivity2']['xrange']),
                yaxis=dict(range=[min(d.min() for d in plotData['sensitivity2']['ydata'][comm].values()),
                                  max(d.max() for d in plotData['sensitivity2']['ydata'][comm].values())]),
            )

            # add annotation above subplot
            self._addAnnotation(fig, c, 'Case 1 only', row=4)

            # add row 3
            xdata = plotData['sensitivity3']['xdata']
            ydata = plotData['sensitivity3']['ydata'][comm]
            self.__addRow3(fig, c, xdata, ydata, mergedDataComm, epdcaseDiffs)

            # update axes row 3
            self._updateAxisLayout(
                fig, c+6,
                xaxis=dict(range=plotData['sensitivity3']['xrange']),
                yaxis=dict(range=[min(d.min() for d in plotData['sensitivity3']['ydata'][comm].values()),
                                  max(d.max() for d in plotData['sensitivity3']['ydata'][comm].values())]),
            )

            # add row 4
            xdata = plotData['sensitivity4']['xdata']
            ydata = plotData['sensitivity4']['ydata']
            zdata = plotData['sensitivity4']['zdata'][comm]
            self.__addRow4(fig, c, xdata, ydata, zdata, mergedDataComm, epdcaseDiffs)

            # update axes row 4
            self._updateAxisLayout(
                fig, c+9,
                xaxis=dict(range=plotData['sensitivity4']['xrange']),
                yaxis=dict(range=plotData['sensitivity4']['yrange'], showticklabels=False),
            )

            # add annotation above subplot
            self._addAnnotation(fig, c, 'Case 1 only', row=2)


        # update layout
        fig.update_layout(
            **{f"xaxis{i*3+2}_title": self._config[f"sensitivity{i+1}"]['xaxislabel'] for i in range(4)},
            **{f"yaxis{i*3+1}": dict(title=self._config[f"sensitivity{i+1}"]['yaxislabel'], showticklabels=True) for i in range(4)},
        )


        return fig


    def __addRow1(self, fig: go.Figure, c: int, xdata: np.ndarray, ydata: dict,
                  mergedDataComm: pd.DataFrame, epdcase: str):

        # loop over cases
        for case, caseData in ydata.items():
            # add lines
            fig.add_trace(
                go.Scatter(
                    x=xdata,
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
                    hovertemplate=f"<b>{case}</b><br>{self._config['sensitivity1']['xlabelshort']}: %{{x:.2f}}<br>{self._config['sensitivity1']['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                row=1,
                col=c + 1,
            )

            # add points
            thisData = mergedDataComm.query(f"case=='{case}'")
            fig.add_trace(
                go.Scatter(
                    x=thisData['irate'],
                    y=thisData[f"val_tot_{epdcase}_diff"],
                    mode='markers',
                    text=case,
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

        for irate in mergedDataComm['irate'].unique():
            fig.add_trace(
                go.Scatter(
                    x=[irate, irate],
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


    def __addRow2(self, fig: go.Figure, c: int, xdata: np.ndarray, ydata: dict,
                  mergedDataComm: pd.DataFrame, epdcaseDiffs: pd.Series):

        # dashed lines
        for htc in mergedDataComm['specH2TranspCost'].unique():
            fig.add_trace(
                go.Scatter(
                    x=[htc, htc],
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

        # loop over epdcases
        for epdcase, caseData in ydata.items():
            case = 'Case 1A'
            # add lines
            fig.add_trace(
                go.Scatter(
                    x=xdata,
                    y=caseData,
                    mode='lines',
                    legendgroup=case,
                    showlegend=False,
                    line=dict(
                        color=self._config['line_colour'][case],
                        width=self._config['global']['lw_thin'],
                    ),
                    hovertemplate=f"<b>{case}</b><br>{self._config['sensitivity2']['xlabelshort']}: %{{x:.2f}}<br>{self._config['sensitivity2']['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                row=2,
                col=c + 1,
            )

            # add points
            cases = ['Case 1A', 'Case 1B']
            thisData = mergedDataComm.query(f"case in {cases}")
            fig.add_trace(
                go.Scatter(
                    x=thisData['specH2TranspCost'],
                    y=thisData[f"val_tot_{epdcase}_diff"],
                    mode='markers+text',
                    text=f"{epdcaseDiffs[epdcase]:.0f}",
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
                    textfont_color=self._config['line_colour'][case],
                    textposition='top left',
                ),
                row=2,
                col=c + 1,
            )


    def __addRow3(self, fig: go.Figure, c: int, xdata: np.ndarray, ydata: dict,
                  mergedDataComm: pd.DataFrame, epdcaseDiffs: pd.Series):
        # add dashed vlines in the background
        for epdiff in epdcaseDiffs.values:
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
                row=3,
                col=c + 1,
            )

        # loop over cases
        for case, caseData in ydata.items():
            # add lines
            fig.add_trace(
                go.Scatter(
                    x=xdata,
                    y=caseData,
                    mode='lines',
                    name=case,
                    legendgroup=case,
                    showlegend=False,
                    line=dict(
                        color=self._config['line_colour'][case],
                        width=self._config['global']['lw_thin'],
                        dash='dash' if case=='Case 1A' else 'solid',
                    ),
                    hovertemplate=f"<b>{case}</b><br>{self._config['sensitivity3']['xlabelshort']}: %{{x:.2f}}<br>{self._config['sensitivity3']['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                row=3,
                col=c + 1,
            )

            # add points
            thisData = mergedDataComm.query(f"case=='{case}'")
            for epdcase, epdiff in epdcaseDiffs.items():
                fig.add_trace(
                    go.Scatter(
                        x=[epdiff],
                        y=[thisData[f"val_tot_{epdcase}_diff"].iloc[0]],
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
                    row=3,
                    col=c + 1,
                )


    def __addRow4(self, fig: go.Figure, c: int, xdata: np.ndarray, ydata: np.ndarray, zdata: np.ndarray,
                  mergedDataComm: pd.DataFrame, epdcaseDiffs: pd.Series):
        colbarlen = (1.0-(self.__nrows-1)*self.__vspc) / self.__nrows

        fig.add_trace(
            go.Heatmap(
                x=xdata,
                y=ydata,
                z=zdata,
                zsmooth='best',
                zmin=self._config['sensitivity4']['zrange'][0],
                zmax=self._config['sensitivity4']['zrange'][1],
                colorscale=[
                    [i/(len(self._config['sensitivity4']['zcolours'])-1), colour]
                    for i, colour in enumerate(self._config['sensitivity4']['zcolours'])
                ],
                colorbar=dict(
                    x=1.01,
                    y=colbarlen/2,
                    yanchor='middle',
                    len=colbarlen,
                    title=self._config['sensitivity4']['zaxislabel'],
                    titleside='right',
                    tickvals=[float(t) for t in self._config['sensitivity4']['zticks']],
                    ticktext=self._config['sensitivity4']['zticks'],
                    titlefont_size=self._getFontSize('fs_sm'),
                ),
                showscale=not c,
                hoverinfo='skip',
            ),
            row=4,
            col=c + 1,
        )

        fig.add_trace(
            go.Contour(
                x=xdata,
                y=ydata,
                z=zdata,
                contours_coloring='lines',
                colorscale=[
                    [0.0, '#000000'],
                    [1.0, '#000000'],
                ],
                line_width=self._config['global']['lw_ultrathin'],
                contours=dict(
                    showlabels=True,
                    start=self._config['sensitivity4']['zrange'][0],
                    end=self._config['sensitivity4']['zrange'][1],
                    size=self._config['sensitivity4']['zdelta'],
                ),
                showscale=False,
                hoverinfo='skip',
            ),
            row=4,
            col=c + 1,
        )

        # add dashed vlines in the background
        for epdiff in epdcaseDiffs.values:
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
                row=4,
                col=c + 1,
            )

        # add Case 1 lines and points
        for case in ['Case 1A', 'Case 1B']:
            thisData = mergedDataComm.query(f"case=='{case}'")
            y = thisData['specH2TranspCost'].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=xdata,
                    y=[y for _ in xdata],
                    mode='lines',
                    name=case,
                    line=dict(
                        color=self._config['line_colour'][case],
                        width=self._config['global']['lw_thin'],
                        dash='dash' if case=='Case 1A' else 'solid',
                    ),
                    showlegend=False,
                ),
                row=4,
                col=c + 1,
            )

            fig.add_trace(
                go.Scatter(
                    x=epdcaseDiffs.values,
                    y=len(epdcaseDiffs.values) * [y],
                    mode='markers',
                    text=case,
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
                row=4,
                col=c + 1,
            )
