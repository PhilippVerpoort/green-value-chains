import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from posted.calc_routines.LCOX import LCOX
from posted.config.config import flowTypes, techs

from src.utils import loadYAMLConfigFile
from src.plots.BasePlot import BasePlot


class LevelisedPlot(BasePlot):
    figs = loadYAMLConfigFile(f"figures/LevelisedPlot")
    _addSubfigName = True

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        super(LevelisedPlot, self)._decorate(inputs, outputs, subfigs)

        # loop over commodities (three columns)
        commodities = list(inputs['value_chains'].keys())
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for subfigPlot in subfigs.values():
                self._addAnnotationComm(subfigPlot, comm, c)

    typeMapping = {
        r'^cap$': 'capital',
        r'^fop$': 'fonmco',
        r'^transp_cost:.*$': 'transport',
        r'^dem_cost:elec$': 'elec',
        r'^dem_cost:(coal|ng)$': 'energy',
        r'^dem_cost:\b(?!(elec|coal|ng))\b.*$': 'rawmat',
    }

    def plot(self, inputs: dict, outputs: dict, subfigNames: list) -> dict:
        cfg = self._figCfgs['fig5']
        commodities = list(inputs['value_chains'].keys())

        # create figure
        fig = make_subplots(
            cols=len(commodities),
            horizontal_spacing=0.035,
        )

        # add bars for each subplot
        for c, comm in enumerate(commodities):
            commData = self.__prepare(outputs, comm, cfg)

            ymax = self.__addBars(fig, c, commData)

            self.__addArrows(fig, c)

            # update layout of subplot
            self._updateAxisLayout(fig, c,
                xaxis=dict(
                    title='',
                    categoryorder='array',
                    categoryarray=sorted(commData['impcase_display']),
                ),
                yaxis=dict(
                    title='',
                    range=[0.0, ymax]
                ),
            )

            # add cost differences from Base Case
            if self._target == 'print':
               self.__addCostDiff(fig, c, commData, ymax)

        # update layout of all plots
        fig.update_layout(
            barmode='stack',
            yaxis_title=cfg['yaxis_title'],
            legend_title='',
        )

        return {'fig5': fig}

    def __prepare(self, outputs: dict, comm: str, cfg: dict):
        # produce LCOX DataTable by assuming final elec prices and applying calc routine
        lcox = outputs['tables'][comm] \
            .assume(outputs['cases'][comm]) \
            .calc(LCOX)

        # extract dataframe from LCOX DataTable and convert to plottable format
        commData = lcox.data['LCOX'] \
            .pint.dequantify().droplevel('unit', axis=1) \
            .stack(['process', 'type']).to_frame('value') \
            .reset_index() \
            .query(f"epdcase=='{cfg['epdcase']}'") \
            .drop(columns=['epdcase'])

        # map types
        commData['ptype'] = commData['type'].replace(regex=self.typeMapping)

        # rename import cases (1 to 1A/B and add subtitles)
        commData['impcase_display'] = commData['impcase'] \
            .map({
                caseName: f"<b>{caseName + ('A/B' if caseName == 'Case 1' else '')}</b>:<br>{caseDesc}"
                for caseName, caseDesc in self._globCfg['globPlot']['case_names'].items()
            })

        # prepare hover data
        if self._target == 'webapp':
            commData['hover_ptype'] = commData['ptype'].map({
                ptype: display['label']
                for ptype, display in self._globCfg['globPlot']['cost_types'].items()
            })
            commData['hover_flow'] = commData['type'].map({
                f"dem_cost:{flowid}": flowSpecs['name']
                for flowid, flowSpecs in flowTypes.items()
            } | {
                f"transp_cost:{flowid}": flowSpecs['name']
                for flowid, flowSpecs in flowTypes.items()
            })
            commData['hover_proc'] = commData['process'].map({
                tid: techSpecs['name']
                for tid, techSpecs in techs.items()
            })

        return commData

    # add stacked bars showing levelised cost components
    def __addBars(self, fig: go.Figure, c: int, commData: pd.DataFrame):
        # determine ymax
        ymax = (1.15 if self._target == 'print' else 1.05) * commData.query("impcase=='Base Case'").value.sum()

        # split up into main data and h2 cases data
        mainData = commData.query("impsubcase!='Case 1A' & type!='transp_cost:h2'").assign(impsubcase=lambda df: df['impcase'])
        h2transpData = commData.query("impcase=='Case 1' & type=='transp_cost:h2'")

        # prepare hover info
        hover = self._target == 'webapp'
        hovercols = ['impsubcase', 'hover_ptype', 'hover_flow', 'hover_proc', 'value'] if hover else None
        hovercomp = {
            'header_basic': '<b>%{customdata[1]}</b><br>',
            'header_flow': '<b>%{customdata[1]} (%{customdata[2]})</b><br>',
            'impcase': 'Import case: %{customdata[0]}<br>',
            'process': 'Process: %{customdata[3]}<br>',
            'cost': 'Cost: %{customdata[4]} EUR/t',
            'extra': '<extra></extra>',
        }
        hovertemplateBasic = ''.join(hovercomp[c] for c in ['header_basic', 'impcase', 'process', 'cost', 'extra'])
        hovertemplateFlow = ''.join(hovercomp[c] for c in ['header_flow', 'impcase', 'process', 'cost', 'extra'])
        hovertemplateTransp = ''.join(hovercomp[c] for c in ['header_flow', 'impcase', 'cost', 'extra'])

        # add traces for all cost types
        for ptype, display in self._globCfg['globPlot']['cost_types'].items():
            thisData = mainData \
                .query(f"ptype=='{ptype}'") \
                .sort_index(level='impcase') \

            if self._target == 'print':
                thisData = thisData \
                    .groupby(['ptype', 'impcase_display']) \
                    .agg({'value': 'sum'}) \
                    .reset_index()

            # for hover template determine if this type has a flow associated
            hovertemplate = (
                None if not hover else
                hovertemplateTransp if ptype == 'transport' else
                hovertemplateFlow if ptype != 'elec' and thisData['hover_flow'].notna().all() else
                hovertemplateBasic
            )

            fig.add_trace(
                go.Bar(
                    x=thisData['impcase_display'],
                    y=thisData['value'],
                    marker_color=display['colour'],
                    name=display['label'],
                    showlegend=not c,
                    width=0.8,
                    hoverinfo='text' if hover else 'skip',
                    hovertemplate=hovertemplate,
                    customdata=thisData[hovercols] if hover else None,
                ),
                row=1,
                col=c + 1,
            )

        display = self._globCfg['globPlot']['cost_types']['transport']
        baseVal = mainData.query(f"impcase=='Case 1'").value.sum()

        for s, subcase in enumerate(h2transpData.impsubcase.unique()):
            p = h2transpData.query(f"impsubcase=='{subcase}'")
            fig.add_trace(
                go.Bar(
                    x=p['impcase_display'],
                    y=p['value'],
                    base=baseVal,
                    marker_color=display['colour'],
                    name=display['label'],
                    showlegend=False,
                    width=0.4,
                    offset=-0.4 + 0.4 * s,
                    hoverinfo='text' if hover else 'skip',
                    hovertemplate=hovertemplateTransp,
                    customdata=p[hovercols] if hover else None,
                ),
                row=1,
                col=c + 1,
            )


        return ymax

    # add arrows indicating difference between cases
    def __addCostDiff(self, fig, c, commData, ymax):
        correction = 0.018
        xshift = 2.5
        yshift = 35.0

        # select data for each subplot
        baseCost = commData.query("impcase=='Base Case'").value.sum()

        fig.add_hline(
            baseCost,
            line_color='black',
            line_width=self._globCfg['globStyle'][self._target]['lw_thin'],
            row=1,
            col=c + 1,
        )

        for i, impsubcase in enumerate(commData['impsubcase'].unique()[1:]):
            thisCost = commData.query(f"impsubcase=='{impsubcase}'").value.sum()

            costDiff = thisCost - baseCost
            costDiffAbs = abs(costDiff)
            costDiffSign = '+' if costDiff > 0.0 else '-'

            casePos = float(i)+1
            if impsubcase == 'Case 1A':
                casePos -= 0.2
            elif impsubcase == 'Case 1B':
                casePos += 0.2
                casePos -= 1
            if i > 1:
                casePos -= 1

            fig.add_annotation(
                x=casePos,
                y=min(thisCost, ymax),
                yref=f"y{c + 1 if c else ''}",
                ax=casePos,
                ay=baseCost + (correction * ymax if costDiff < 0.0 else -correction * ymax),
                ayref=f"y{c + 1 if c else ''}",
                arrowcolor='black',
                arrowwidth=self._globCfg['globStyle'][self._target]['lw_thin'],
                arrowhead=2,
                row=1,
                col=c + 1,
            )

            fig.add_annotation(
                text=f" {costDiffSign}{costDiffAbs:.1f}<br>({costDiffAbs / baseCost * 100:.1f}%)",
                align='left',
                showarrow=False,
                x=casePos,
                xanchor='left',
                xshift=xshift,
                y=baseCost,
                yanchor='middle',
                yref=f"y{c + 1 if c else ''}",
                yshift=-yshift if impsubcase != 'Case 1A' else +yshift,
                row=1,
                col=c + 1,
            )

    # add arrows explaining the plot
    def __addArrows(self, fig: go.Figure, c: int):
        # top
        xref = f"x{c + 1 if c else ''} domain"
        yref = f"y{c + 1 if c else ''} domain"

        fig.add_annotation(
            showarrow=True,
            text=None,
            ax=0.15,
            ay=0.3,
            axref=xref,
            ayref=yref,
            x=0.85,
            y=0.3,
            xref=xref,
            yref=yref,
            arrowhead=1,
            arrowsize=0.8,
            arrowwidth=4,
            arrowcolor='#000000',
            opacity=1.0,
        )

        fig.add_annotation(
            showarrow=False,
            text='Deeper relocation',
            x=0.5,
            y=0.26,
            xref=xref,
            yref=yref,
        )
