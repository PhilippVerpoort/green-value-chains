from string import ascii_lowercase

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.custom.plots.BasePlot import BasePlot
from src.scaffolding.file.load_default_data import all_processes, all_routes, commodities


class LevelisedPlot(BasePlot):
    _complete = True

    def _prepare(self):
        if self.anyRequired('fig4', 'figS1', 'figS3'):
            self._prep['default'] = self.__makePrep(self._finalData['costData'])

        if self.anyRequired('figS3'):
            self._prep['recycling'] = self.__makePrep(self._finalData['costDataRec'])


    # make adjustments to data (route names, component labels)
    def __makePrep(self, costData: pd.DataFrame):
        # remove upstream cost entries
        costDataNew = costData \
            .query(f"type!='upstream'") \
            .reset_index(drop=True)

        # multiply by electricity prices
        costDataNew = self._finaliseCostData(costDataNew, epdcases=[self._config['epdcase']])

        # split up hydrogen transport cost
        q = "type=='transport' and component=='hydrogen'"
        costDataH2Transp = costDataNew.query(q).reset_index(drop=True)
        costDataNew = costDataNew.query(f"not ({q})").reset_index(drop=True)
        costDataH2Transp['hover_label'] = 'Transport'

        # rename iron feedstock entries
        if self._config['separate_iron']:
            costDataNew.loc[(costDataNew['type'] == 'feedstock') & costDataNew['component'].isin(['ore', 'scrap']), 'type'] = 'iron'

        # determine breakdown level of bars and associated hover labels
        if self._config['aggregate_by'] == 'none':
            costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
            costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
        elif self._config['aggregate_by'] == 'subcomponent':
            costDataNew = self._groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                        ['type', 'period', 'commodity', 'route', 'process', 'component'], keep=['case', 'baseRoute'])
            costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
            costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
        elif self._config['aggregate_by'] == 'component':
            costDataNew = self._groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                        ['type', 'period', 'commodity', 'route', 'process'], keep=['case', 'baseRoute'])
            costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        elif self._config['aggregate_by'] == 'process':
            costDataNew = self._groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                        ['type', 'period', 'commodity', 'route', 'component'], keep=['case', 'baseRoute'])
            costDataNew['hover_label'] = [self._config['components'][c] if c!='empty' else None for c in costDataNew['component']]
        elif self._config['aggregate_by'] == 'all':
            costDataNew = self._groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                        ['type', 'period', 'commodity', 'route'], keep=['case', 'baseRoute'])
            costDataNew['hover_label'] = [self._config['types'][t]['label'] for t in costDataNew['type']]
        else:
            raise Exception('Value of aggregate_by in the plot config is invalid.')

        # sort by commodities
        costDataNew.sort_values(by='commodity', key=lambda row: [commodities.index(c) for c in row], inplace=True)

        return {
            'costDataAgg': costDataNew,
            'costDataH2Transp': costDataH2Transp,
        }


    def _plot(self):
        # produce fig4
        if self.anyRequired('fig4'):
            self._ret['fig4'] = self.__makePlot(**self._prep['default'])

        # produce figS1
        if self.anyRequired('figS1'):
            for k, commodity in enumerate(list(all_routes.keys())):
                subfigName = f"figS1{ascii_lowercase[k]}"
                self._ret[subfigName] = self.__makePlot(**self._prep['default'], mode=commodity)

        # produce figS3
        if self.anyRequired('figS3'):
            self._ret['figS3'] = self.__makePlot(**self._prep['recycling'])

        return self._ret


    def __makePlot(self, costDataAgg: pd.DataFrame, costDataH2Transp: pd.DataFrame, mode: str = ''):
        # determine subplot data to show based on mode
        if mode:
            q = f"commodity=='{mode}'"
            subplots = [int(y) for y in sorted(costDataAgg.period.unique())]
        else:
            q = f"period=={self._config['select_period']} & case.notnull()"
            subplots = commodities

        # query for relevant data, display cases 1A and 1B as same x, add case subtitles
        costDataAgg = costDataAgg \
            .query(q) \
            .assign(displayCase=lambda r: r.case) \
            .replace({'displayCase': ['Case 1A', 'Case 1B']}, 'Case 1A/B') \
            .replace({'displayCase': {caseName: f"<b>{caseName}</b>:<br>{caseDesc}" for caseName, caseDesc in self._config['case_names'].items()}})
        costDataH2Transp = costDataH2Transp \
            .query(q) \
            .assign(displayCase=lambda r: r.case) \
            .replace({'displayCase': ['Case 1A', 'Case 1B']}, 'Case 1A/B') \
            .replace({'displayCase': {caseName: f"<b>{caseName}</b>:<br>{caseDesc}" for caseName, caseDesc in self._config['case_names'].items()}})

        # create figure
        fig = make_subplots(
            cols=len(subplots),
            horizontal_spacing=0.035,
        )

        # add bars for each subplot
        for c, subplot in enumerate(subplots):
            ymax = self.__addBars(fig, c, subplot, mode, costDataAgg, costDataH2Transp)

            # add cost differences from Base Case
            if not self._isWebapp:
                self.__addCostDiff(fig, c, subplot, mode, costDataAgg, costDataH2Transp, ymax)

            # add annotations above subplot
            if mode:
                self._addAnnotation(fig, c, subplot)
            else:
                self._addAnnotationComm(fig, c, subplot)

        # update layout of all plots
        fig.update_layout(
            barmode='stack',
            yaxis_title=self._config['yaxislabel'],
            legend_title='',
        )

        return fig


    def __addBars(self, fig: go.Figure, c: int, subplot: str, mode: str,
                  costData: pd.DataFrame, costDataH2Transp: pd.DataFrame):
        # select data for each subplot
        plotData = costData \
            .query(f"period=={subplot}" if mode else f"commodity=='{subplot}'") \
            .query("case!='Case 1B'") \
            .sort_values(by='case')
        # select H2 transp cost data
        plotDataH2Transp = costDataH2Transp.query(f"period=={subplot}" if mode else f"commodity=='{subplot}'")

        # determine ymax
        if self._config['ymaxcalc']:
            ymax = 1.15 * plotData.query("case=='Base Case'").val.sum()
        else:
            ymax = self._config['ymax'][mode] if mode else self._config['ymax'][subplot]

        # whether a hover label should be set
        hoverLabel = 'hover_label' in plotData.columns and any(plotData.hover_label.unique())

        # add traces for all cost types
        for type, display in self._config['cost_types'].items():
            thisData = plotData.query(f"type=='{type}'")

            fig.add_trace(
                go.Bar(
                    x=thisData.displayCase,
                    y=thisData.val,
                    marker_color=display['colour'],
                    name=display['label'],
                    customdata=thisData.hover_label if hoverLabel else None,
                    showlegend=not c,
                    hovertemplate=f"<b>{display['label']}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>Cost: %{{y}} EUR/t<extra></extra>",
                    width=0.8,
                ),
                row=1,
                col=c + 1,
            )

        display = self._config['cost_types']['transport']
        baseVal = plotData.query(f"case in ['Case 1A', 'Case 1B']").val.sum()

        for m, case in enumerate(plotDataH2Transp.case.unique()):
            p = plotDataH2Transp.query(f"case=='{case}'")

            fig.add_trace(
                go.Bar(
                    x=p.displayCase,
                    y=p.val,
                    base=baseVal,
                    marker_color=display['colour'],
                    name=display['label'],
                    customdata=p.hover_label if hoverLabel else None,
                    showlegend=False,
                    hovertemplate=f"<b>{display['label']}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>Cost: %{{y}} EUR/t<extra></extra>",
                    width=0.4,
                    offset=-0.4 + 0.4 * m,
                ),
                row=1,
                col=c + 1,
            )

        # update layout of subplot
        fig.update_layout(
            **{
                f"xaxis{c + 1 if c else ''}": dict(title=''),
                f"yaxis{c + 1 if c else ''}": dict(title='', range=[0.0, ymax]),
            },
        )

        return ymax


    def __addCostDiff(self, fig, c, subplot, mode, costData, costDataH2Transp, ymax):
        correction = 0.018
        xshift = 2.5
        yshift = 35.0

        # select data for each subplot
        plotData = pd.concat([costData, costDataH2Transp]) \
            .query(f"period=={subplot}" if mode else f"commodity=='{subplot}'") \
            .sort_values(by='case')
        baseCost = plotData.query("case=='Base Case'").val.sum()

        fig.add_hline(
            baseCost,
            line_color='black',
            line_width=self._config['global']['lw_thin'],
            row=1,
            col=c + 1,
        )

        for case, caseName in enumerate(plotData.case.unique()[1:]):
            thisCost = plotData.query(f"case=='{caseName}'").val.sum()

            costDiff = thisCost - baseCost
            costDiffAbs = abs(costDiff)
            costDiffSign = '+' if costDiff > 0.0 else '-'

            casePos = float(case)+1
            if caseName == 'Case 1A':
                casePos -= 0.2
            elif caseName == 'Case 1B':
                casePos += 0.2
                casePos -= 1
            if case > 1:
                casePos -= 1

            fig.add_annotation(
                x=casePos,
                y=min(thisCost, ymax),
                yref=f"y{c + 1 if c else ''}",
                ax=casePos,
                ay=baseCost + (correction * ymax if costDiff < 0.0 else -correction * ymax),
                ayref=f"y{c + 1 if c else ''}",
                arrowcolor='black',
                arrowwidth=self._config['global']['lw_thin'],
                arrowhead=2,
                row=1,
                col=c + 1,
            )

            y = thisCost + (costDiffAbs / 2 if costDiff < 0.0 else -costDiffAbs / 2)
            if c==1 and caseName == 'Case 1A':
                y = thisCost - 3/4*costDiffAbs
            fig.add_annotation(
                text=f" {costDiffSign}{costDiffAbs:.1f}<br>({costDiffSign}{costDiffAbs / baseCost * 100:.1f}%)",
                align='left',
                showarrow=False,
                x=casePos,
                xanchor='left',
                xshift=xshift,
                y=baseCost,
                yref=f"y{c + 1 if c else ''}",
                yanchor='middle',
                yshift=-yshift if costDiff < 0.0 else +yshift,
                row=1,
                col=c + 1,
            )
