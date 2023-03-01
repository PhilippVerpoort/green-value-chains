import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import all_processes, all_routes, commodities


class RelocationAnalysisPlot(BasePlot):
    _complete = True

    def _decorate(self):
        super(RelocationAnalysisPlot, self)._decorate()

        # loop over commodities (three columns)
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for fig in self._ret.values():
                self._addAnnotationComm(fig, c, comm)

    def _prepare(self):
        if self.anyRequired('fig5', 'figS5'):
            self._prep = self.__makePrep(self._finalData['costData'])


    # make adjustments to data before plotting
    def __makePrep(self, costData: pd.DataFrame):
        # drop non-case routes, select period and drop unused period column
        costDataNew = costData \
            .query(f"case.notnull() & period=={self._config['select_period']}") \
            .drop(columns=['period']) \
            .reset_index(drop=True)

        # insert final electricity prices
        costDataNew = self._finaliseCostData(costDataNew, epdcases=['upper', 'default', 'lower'], epperiod=self._config['select_period'])

        # modify data for each commodity
        costDataLevelised = []
        costDataRelocationList = []
        processesOrdered = {}
        for comm in commodities:
            costDataComm = costDataNew \
                .query(f"commodity=='{comm}'") \
                .reset_index(drop=True)

            # get processes in the route
            processes = [p for p in all_routes[comm][costDataComm.baseRoute.iloc[0]]['processes'].keys() if p in costDataComm.process.unique()]
            processesShown = [p for p in processes if p not in self._config['map_processes']]

            # save list of processes, so they are displayed in the correct order
            processesOrdered[comm] = processesShown if not self._config['show_mapped'] else processes

            # map DAC and heat pump to their associated main processes
            if not self._config['show_mapped']:
                processMapping = {}
                for p in self._config['map_processes']:
                    if p not in processes: continue
                    processMapping[p] = next(pMapped for pMapped in processes[processes.index(p)+1:] if pMapped not in self._config['map_processes'])
                costDataComm.loc[:, 'process'] = costDataComm.loc[:, 'process'].replace(processMapping)

            # drop non-default epd cases
            costDataLevelisedComm = costDataComm.query(f"epdcase=='{self._config['select_epdcase']}' & case=='{self._config['select_case']}'")

            # add upstream data for plotting
            for i, p in enumerate(processes[:-1]):
                upstreamCostData = costDataLevelisedComm.query(f"process=='{p}'").assign(type='upstream')
                costDataLevelisedComm = pd.concat([costDataLevelisedComm, upstreamCostData.assign(process=processes[i+1])], ignore_index=True)

            # replace non-energy types with generic label
            processMapping = {t: 'non-energy' for t in costData['type'] if t!='energy'}
            costDataLevelisedComm = costDataLevelisedComm.replace({'type': processMapping})

            # aggregate data, keep process, type, and case
            costDataLevelisedComm = self._groupbySumval(costDataLevelisedComm, ['process', 'type'], keep=['commodity'])

            # determine relative shares
            costDataLevelisedComm = costDataLevelisedComm \
                .merge(
                    self._groupbySumval(costDataLevelisedComm.query(f"type!='upstream'"), ['process']).rename(columns={"val": "val_tot"}),
                    on=['process'],
                ) \
                .assign(val_rel=lambda r: r.val / r.val_tot * 100.0)

            # add process labels
            costDataLevelisedComm['process_label'] = [all_processes[p]['short'] for p in costDataLevelisedComm['process']]

            # append data
            costDataLevelised.append(costDataLevelisedComm)

            # determine share of value creation retained
            relocations = [
                (0, 'Base Case', 'Case 1A'),
                (0, 'Base Case', 'Case 1B'),
                (1, 'Case 1A', 'Case 2'),
                (1, 'Case 1B', 'Case 2'),
                (2, 'Case 2', 'Case 3'),
            ]
            costDataCommValAdd = costDataComm.query(f"type!='energy' & type!='transport' & case=='Base Case' & epdcase=='default'")
            for pid, caseFrom, caseTo in relocations:
                processesRetainedFrom = processesShown[pid:]
                processesRetainedTo = processesShown[pid+1:]

                # determine share of value added retained
                costDataRetained = self._groupbySumval(costDataCommValAdd, ['case'], keep=['commodity', 'case']) \
                    .merge(
                        self._groupbySumval(costDataCommValAdd.query(f"process in @processesRetainedFrom"), ['case'], keep=['commodity']),
                        on=['commodity', 'case'],
                        suffixes=('', '_retained_from'),
                    ) \
                    .merge(
                        self._groupbySumval(costDataCommValAdd.query(f"process in @processesRetainedTo"), ['case'], keep=['commodity']),
                        on=['commodity', 'case'],
                        how='outer',
                        suffixes=('', '_retained_to'),
                    ) \
                    .fillna(0.0) \
                    .assign(val_marg_share_lost=lambda r: (r.val_retained_from - r.val_retained_to) / r.val * 100.0) \
                    .drop(columns=['val_retained_from', 'val_retained_to', 'val', 'case'])

                # determine marginal relocation savings
                costDataRelocation = self._groupbySumval(costDataComm.query(f"case=='Base Case'"), ['epdcase'], keep=['commodity', 'case', 'epdiff']) \
                    .merge(
                        self._groupbySumval(costDataComm.query(f"case=='{caseFrom}'"), ['epdcase'], keep=['commodity', 'case', 'epdiff']),
                        on=['commodity', 'epdcase', 'epdiff'],
                        suffixes=('', '_from'),
                    ) \
                    .merge(
                        self._groupbySumval(costDataComm.query(f"case=='{caseTo}'"), ['epdcase'], keep=['commodity', 'case', 'epdiff']),
                        on=['commodity', 'epdcase', 'epdiff'],
                        suffixes=('', '_to'),
                    ) \
                    .assign(val_marg_savings=lambda r: (r.val_from - r.val_to) / r.val * 100.0, case_switch=lambda r: r.case_from + r.case_to) \
                    .drop(columns=['val_from', 'val_to'])

                # skip case 1A
                if 'Case 1A' in [caseFrom, caseTo]:
                    continue

                # append data
                costDataRelocationList.append(
                    pd.merge(costDataRetained, costDataRelocation, on=['commodity']).assign(processRelocated=all_processes[processesShown[pid]]['short'])
                )


        return {
            'costDataLevelised': pd.concat(costDataLevelised),
            'costDataRelocation': pd.concat(costDataRelocationList),
            'processesOrdered': processesOrdered,
        }


    def _plot(self):
        # make fig5
        if self.anyRequired('fig5'):
            self._ret['fig5'] = self.__makeMainPlot(**self._prep)

        # make figS5
        if self.anyRequired('figS5'):
            self._ret['figS5'] = self.__makeAppendixPlot(self._prep['costDataLevelised'], self._prep['processesOrdered'])


    def __makeMainPlot(self, costDataLevelised: pd.DataFrame, costDataRelocation: pd.DataFrame, processesOrdered: dict):
        # remove upstream data
        costDataLevelised = costDataLevelised \
            .query(f"type!='upstream'") \
            .reset_index(drop=True)

        # create figure
        hspcng = 0.04
        fig = make_subplots(
            cols=len(commodities),
            rows=2,
            horizontal_spacing=hspcng,
        )

        # add bars for each subplot
        for c, comm in enumerate(commodities):
            # plot data for commodity
            costDataComm = costDataLevelised.query(f"commodity=='{comm}'")
            costDataRelComm = costDataRelocation.query(f"commodity=='{comm}'")

            # add plots to top row
            self.__addTop(c, comm, costDataComm, fig, processesOrdered[comm])

            # update top axes layout
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(title='', categoryorder='array', categoryarray=[
                    all_processes[p]['short'] for p in processesOrdered[comm] if p in costDataComm.process.unique()
                ]),
                yaxis=dict(title='', range=[0.0, 100.0]),
            )

            # add plots to top row
            self.__addBottom(c, comm, costDataRelComm, fig, processesOrdered[comm])

        # update layout of all plots
        fig.update_layout(
            barmode='stack',
            xaxis2_title=self._config['top']['xaxislabel'],
            yaxis_title=self._config['top']['yaxislabel'],
            xaxis5_title=self._config['bottom']['xaxislabel'],
            yaxis4_title=self._config['bottom']['yaxislabel'],
            legend_title='',
        )

        return fig

    def __addTop(self, c: int, comm: str, costDataComm: pd.DataFrame, fig: go.Figure, processesOrdered: list):
        hasLegend = []
        for i, p in enumerate(processesOrdered):
            # plot data for individual process
            thisDataProc = costDataComm.query(f"process=='{p}'")

            # add bar charts
            showTypes = [(t, d) for t, d in self._config['cost_types'].items() if t in costDataComm.type.unique()]
            for type, display in showTypes:
                plotDataProcType = thisDataProc.query(f"type=='{type}'")

                fig.add_trace(
                    go.Bar(
                        x=plotDataProcType.process_label,
                        y=plotDataProcType.val_rel,
                        marker_color=display['colour'],
                        name=display['label'],
                        hovertemplate=f"<b>{display['label']}</b><br>Cost: %{{y}} EUR/t<extra></extra>",
                        showlegend=not c and type not in hasLegend,
                        legendgroup=type,
                    ),
                    row=1,
                    col=c + 1,
                )

                if not c and type not in hasLegend and not plotDataProcType.empty:
                    hasLegend.append(type)


    def __addBottom(self, c: int, comm: str, costDataRelComm: pd.DataFrame, fig: go.Figure, processesOrdered: list):
        for caseSwitch in costDataRelComm.case_switch.unique():
            thisData = costDataRelComm.query(f"case_switch=='{caseSwitch}'")

            fig.add_trace(
                go.Scatter(
                    x=thisData.val_marg_savings,
                    y=thisData.val_marg_share_lost,
                    name=comm,
                    mode='markers+lines',
                    marker=dict(
                        color=self._config['commodity_colours'][comm],
                        symbol=self._config['symbol'],
                        size=self._config['global']['marker_sm'],
                        line_width=self._config['global']['lw_thin'],
                        line_color=self._config['commodity_colours'][comm],
                    ),
                    showlegend=False,
                    legendgroup=comm,
                ),
                row=2,
                col=c + 1,
            )

            # epd annotations
            fig.add_trace(
                go.Scatter(
                    x=thisData.val_marg_savings,
                    y=thisData.val_marg_share_lost,
                    text=thisData.epdiff,
                    name=comm,
                    mode='markers+text',
                    textposition='bottom center',
                    textfont_size=self._getFontSize('fs_tn'),
                    textfont_color=self._config['commodity_colours'][comm],
                    marker_size=self._config['global']['marker_sm'],
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    legendgroup=comm,
                ),
                row=2,
                col=c + 1,
            )

            # case annotations
            caseName = thisData.query(f"epdcase=='default'")
            fig.add_trace(
                go.Scatter(
                    x=caseName.val_marg_savings,
                    y=caseName.val_marg_share_lost,
                    text=caseName.processRelocated,
                    name=comm,
                    mode='markers+text',
                    textposition='top center',
                    textfont_size=self._getFontSize('fs_sm'),
                    textfont_color=self._config['commodity_colours'][comm],
                    marker_size=self._config['global']['marker_sm'],
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    legendgroup=comm,
                ),
                row=2,
                col=c + 1,
            )

    def __makeAppendixPlot(self, costDataLevelised: pd.DataFrame, processesOrdered: dict):
        # create figure
        hspcng = 0.04
        fig = make_subplots(
            cols=len(commodities),
            horizontal_spacing=hspcng,
        )

        # add bars for each subplot
        showTypes = [(t, d) for t, d in self._config['cost_types'].items() if t in costDataLevelised.type.unique()]
        hasLegend = []
        for c, comm in enumerate(commodities):
            # plot data for commodity
            costDataComm = costDataLevelised.query(f"commodity=='{comm}'")

            # determine ymax
            ymax = 1.2 * costDataComm.query(f"type!='upstream'").val.sum()

            for i, p in enumerate(processesOrdered[comm]):
                # plot data for individual process
                thisDataProc = costDataComm.query(f"process=='{p}'")

                # determine spacing of pie charts
                w1 = (1.0 - hspcng * (len(commodities) - 1)) / len(commodities)
                w2 = w1 / len(processesOrdered[comm])

                size = 0.10
                spacing = 0.04

                xstart = c * (w1 + hspcng) + i * w2
                xend = c * (w1 + hspcng) + (i + 1) * w2
                ypos = thisDataProc.val.sum() / ymax + size / 2 + spacing

                # add pie charts
                plotDataPie = thisDataProc.query(f"type!='upstream'")
                fig.add_trace(go.Pie(
                    labels=plotDataPie.replace({'type': {t: d['label'] for t, d in showTypes}}).type,
                    values=plotDataPie.val,
                    marker_colors=plotDataPie.replace({'type': {t: d['colour'] for t, d in showTypes}}).type,
                    hovertemplate=f"<b>{all_processes[p]['label']}</b><br>%{{label}}<extra></extra>",
                    showlegend=False,
                    domain=dict(
                        x=[xstart, xend],
                        y=[ypos - size / 2, ypos + size / 2],
                    ),
                ))

                # add bar charts
                base = 0.0
                for type, display in showTypes:
                    plotDataProcType = thisDataProc.query(f"type=='{type}'")
                    addHeight = plotDataProcType.val.sum()

                    if type == 'upstream' and p in self._config['map_processes']:
                        base += addHeight
                        continue

                    fig.add_trace(
                        go.Bar(
                            x=plotDataProcType.process_label,
                            y=plotDataProcType.val,
                            base=base,
                            marker_color=display['colour'],
                            name=display['label'],
                            hovertemplate=f"<b>{display['label']}</b><br>Cost: %{{y}} EUR/t<extra></extra>",
                            showlegend=type not in hasLegend,
                            legendgroup=type,
                        ),
                        row=1,
                        col=c + 1,
                    )

                    base += addHeight

                    if type not in hasLegend and not plotDataProcType.empty:
                        hasLegend.append(type)

            # update axes layout
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(title='', categoryorder='array', categoryarray=[
                    all_processes[p]['short'] for p in processesOrdered[comm] if p in costDataComm.process.unique()
                ]),
                yaxis=dict(title='', range=[0.0, ymax]),
            )

        # update layout of all plots
        fig.update_layout(
            barmode='stack',
            xaxis2_title=self._config['appendix']['xaxislabel'],
            yaxis_title=self._config['appendix']['yaxislabel'],
            legend_title='',
        )

        return fig
