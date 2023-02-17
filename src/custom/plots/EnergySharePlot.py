import re

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import all_processes, all_routes, commodities


class EnergySharePlot(BasePlot):
    _complete = True

    def _prepare(self):
        if self.anyRequired('fig5'):
            self._prep = self.__makePrep(self._finalData['costData'])


    # make adjustments to data before plotting
    def __makePrep(self, costData: pd.DataFrame):
        # drop non-case routes
        costDataNew = costData \
            .query(f"case.notnull()") \
            .reset_index(drop=True)

        # multiply by electricity prices
        costDataNew = self._finaliseCostData(costDataNew, epdcases=[self._config['epdcase']])

        # map DAC and heat pump to their associated main processes
        if self._config['map_processes']:
            for comm, main_proc in [('Urea', 'UREA'), ('Ethylene', 'MEOH')]:
                mapping = {p: main_proc for p in ['HP', 'DAC']}
                rows = costDataNew['commodity']==comm
                costDataNew.loc[rows, 'process'] = costDataNew.loc[rows, 'process'].replace(mapping)

        # replace non-energy types with generic label
        if self._config['simplify_types']:
            mapping = {t: 'non-energy' for t in costData['type'] if t!='energy'}
            costDataNew = costDataNew.replace({'type': mapping})

        # modify data for each commodity
        retData = []
        processesOrdered = {}
        for comm in commodities:
            # query relevant commodity data for given route
            costDataComm = costDataNew\
                .query(f"commodity=='{comm}' & case=='{self._config['import_route'][comm]}' & period=={self._config['select_period']}")\
                .drop(columns=['route', 'case', 'period'])

            # get processes in the route
            processes = [p for p in all_routes[comm][costDataComm.baseRoute.iloc[0]]['processes'].keys() if p in costDataComm.process.unique()]

            # add upstream data for plotting
            for i, p in enumerate(processes[:-1]):
                upstreamCostData = costDataComm.query(f"process=='{p}'").assign(type='upstream')
                costDataComm = pd.concat([costDataComm, upstreamCostData.assign(process=processes[i+1])], ignore_index=True)

            # aggregate data over processes and types
            costDataComm = self._groupbySumval(costDataComm, ['commodity', 'process', 'type'])

            # add process labels
            costDataComm['process_label'] = [all_processes[p]['short'] for p in costDataComm['process']]

            # append data
            retData.append(costDataComm)

            # save list of processes, so they display in the correct order
            processesOrdered[comm] = processes


        return {
            'costData': pd.concat(retData),
            'processesOrdered': processesOrdered,
        }


    def _plot(self):
        # make fig5
        if self.anyRequired('fig5'):
            self._ret['fig5'] = self.__makePlot(**self._prep)


    def __makePlot(self, costData: pd.DataFrame, processesOrdered: dict):
        commodities = costData.commodity.unique().tolist()

        # create figure
        hspcng = 0.04
        fig = make_subplots(
            cols=len(commodities),
            horizontal_spacing=hspcng,
        )

        # add bars for each subplot
        showTypes = [(t, d) for t, d in self._config['cost_types'].items() if t in costData.type.unique()]
        hasLegend = []
        for c, comm in enumerate(commodities):
            # plot data for commodity
            plotData = costData.query(f"commodity=='{comm}'")

            # determine ymax
            ymax = 1.2 * plotData.query("type!='upstream'").val.sum()

            for i, p in enumerate(processesOrdered[comm]):
                # plot data for individual process
                plotDataProc = plotData.query(f"process=='{p}'")

                # determine spacing of pie charts
                w1 = (1.0 - hspcng * (len(commodities) - 1)) / len(commodities)
                w2 = w1 / len(processesOrdered[comm])

                size = 0.10
                spacing = 0.04

                xstart = c * (w1 + hspcng) + i * w2
                xend = c * (w1 + hspcng) + (i + 1) * w2
                ypos = plotDataProc.val.sum() / ymax + size / 2 + spacing

                # add pie charts
                plotDataPie = plotDataProc.query(f"type!='upstream'")
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
                    plotDataProcType = plotDataProc.query(f"type=='{type}'")
                    addHeight = plotDataProcType.val.sum()

                    if type == 'upstream' and p in self._config['skip_upstream']:
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

            # add annotations
            self._addAnnotationComm(fig, c, comm)

            # update layout of subplot
            fig.update_layout(
                **{
                    f"xaxis{c + 1 if c else ''}": dict(title='', categoryorder='array',
                                                       categoryarray=[all_processes[p]['short'] for p in
                                                                      processesOrdered[comm] if
                                                                      p in plotData.process.unique()]),
                    f"yaxis{c + 1 if c else ''}": dict(title='', range=[0.0, ymax]),
                },
            )

        # update layout of all plots
        fig.update_layout(
            barmode='stack',
            yaxis=dict(title=self._config['yaxislabel']),
            legend_title='',
        )

        return fig
