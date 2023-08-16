import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb
from plotly.subplots import make_subplots
from posted.calc_routines.LCOX import LCOX

from src.utils import loadYAMLConfigFile
from src.plots.BasePlot import BasePlot


class TotalCostPlot(BasePlot):
    figs = loadYAMLConfigFile(f"figures/TotalCostPlot")
    _addSubfigName = True

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        super(TotalCostPlot, self)._decorate(inputs, outputs, subfigs)

        # loop over commodities (three columns)
        commodities = list(inputs['value_chains'].keys())
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for subfigPlot in subfigs.values():
                self._addAnnotationComm(subfigPlot, comm, c)

    def plot(self, inputs: dict, outputs: dict, subfigNames: list) -> dict:
        cfg = self._figCfgs['fig4']
        commodities = list(inputs['value_chains'].keys())

        # create figure
        fig = make_subplots(
            rows=2,
            cols=len(commodities),
            horizontal_spacing=0.035,
        )

        # list of data for generating table
        tableDataList = []

        # add bars for each subplot
        for c, comm in enumerate(commodities):
            commDataTop, commDataBottom, heatmap, axes, tableData = self.__prepareData(outputs, comm, cfg)
            tableDataList.append(tableData)

            # add top plots
            self.__addTop(fig, c, comm, commDataTop, cfg)

            # add zeroline top
            fig.add_hline(100.0, row=1, col=c+1, line_color='black')

            # update top axes layout
            self._updateAxisLayout(
                fig, c,
                xaxis=dict(
                    categoryorder='category ascending',
                    range=[-0.1, +3.65],
                    tickmode='array',
                    tickvals=[i for i in range(commDataTop['impcase'].nunique())],
                    ticktext=[d for d in commDataTop['impcase_display'].unique()]
                ),
                yaxis=dict(
                    domain=[cfg['top']['domain_boundary'], 1.0],
                    showticklabels=False,
                    **cfg['top']['yaxis'],
                ),
            )

            # add bottom plots
            self.__addBottom(fig, c, comm, commDataBottom, heatmap, cfg)

            # update bottom axes layout
            self._updateAxisLayout(fig, c + 3, **axes)

        # add dummy data for legend
        self.__addDummyLegend(fig, cfg)

        # add arrows explaining the plot if not webapp
        if self._target != 'webapp':
            for c in range(len(commodities)):
                self.__addArrows(fig, c)

        # update layout
        fig.update_layout(
            showlegend=True,
            legend=dict(
                title='',
                x=1.01,
                xanchor='left',
                y=cfg['bottom']['domain_boundary'],
                yanchor='top',
            ),
            yaxis_title=cfg['top']['yaxislabel'],
            yaxis_showticklabels=True,
            xaxis5_title=cfg['bottom']['xaxislabel'],
            yaxis4_title=cfg['bottom']['yaxislabel'],
        )

        # print table
        print(pd.concat(tableDataList, axis=1))

        return {'fig4': fig}

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
                row=2,
                col=1,
            )

    def __prepareData(self, outputs: dict, comm: str, cfg: dict):
        # produce LCOX DataTable by assuming final elec prices from epdcases and drop units
        lcox = outputs['tables'][comm] \
            .assume(outputs['cases'][comm]) \
            .calc(LCOX) \
            .data['LCOX'] \
            .pint.dequantify().droplevel('unit', axis=1) \
            .stack(['process', 'type'])

        # prepare epd numbers from epdcase data for merging
        epd = outputs['epd'] \
            .pint.dequantify().droplevel('unit', axis=1) \
            .filter(['epdcase', 'epd']) \
            .drop_duplicates()

        # data for top row: calculate differences to Base Case, then rename import cases (1 to 1A/B and add subtitles),
        # and finally merge epd numbers for epdcases for display in plot
        commDataTop = lcox \
            .groupby(['impcase', 'impsubcase', 'epdcase']) \
            .agg(sum) \
            .unstack('epdcase') \
            .apply(lambda row: 100.0 * row/row[0]) \
            .stack('epdcase') \
            .to_frame('LCOP_rel') \
            .reset_index() \
            .assign(
                impcase_display=lambda df: df['impcase'].map({
                caseName: f"<b>{caseName + ('A/B' if caseName == 'Case 1' else '')}</b>:<br>{caseDesc}"
                for caseName, caseDesc in self._globCfg['globPlot']['case_names'].items()}),
                impcase_x=lambda df: df['impcase'].astype('category').cat.codes,
            ) \
            .merge(epd, on='epdcase')

        # prepare data for table:
        tableData = commDataTop \
            .query("impcase=='Case 3'") \
            .sort_values(by='epd') \
            .assign(**{comm: lambda x: 100.0-x['LCOP_rel']}) \
            .filter(['epdcase', comm]) \
            .set_index('epdcase')

        # data for bottom row: aggregate penalties and savings separately, then calculate differences to Base Case
        commDataBottom = lcox \
            .rename(lambda x: {'dem_cost:elec': 'elec'}.get(x, 'other'), level='type') \
            .groupby(['impcase', 'impsubcase', 'epdcase', 'type']) \
            .agg(sum) \
            .unstack(['type', 'epdcase']) \
            .apply(lambda row: row - row[0]) \
            .stack('epdcase') \
            .reset_index() \
            .merge(epd, on='epdcase')

        # data for heatmap
        dataRange = {
            'xmin': -commDataBottom['elec'].max(), 'xmax': -commDataBottom['elec'].min(),
            'ymin': commDataBottom['other'].min(), 'ymax': commDataBottom['other'].max(),
        }
        plotRange = [
            0.0,
            1.05 * max(dataRange['xmax'], dataRange['ymax']),
        ]

        x = np.linspace(*plotRange, cfg['bottom']['samples'])
        y = np.linspace(*plotRange, cfg['bottom']['samples'])
        vx, vy = np.meshgrid(x, y)
        baseTotal = lcox \
            .reorder_levels(['impcase', 'impsubcase', 'epdcase', 'process', 'type']) \
            .loc['Base Case', 'Base Case', 'medium'] \
            .sum()
        z = ((vx - vy) / baseTotal) * 100.0

        heatmap = {
            'x': x,
            'y': y,
            'z': z,
        }

        axes = {
            'xaxis': dict(range=plotRange),
            'yaxis': dict(range=plotRange, domain=[0.0, cfg['bottom']['domain_boundary']]),
        }

        return commDataTop, commDataBottom, heatmap, axes, tableData

    # add stacked bars showing levelised cost components
    def __addTop(self, fig: go.Figure, c: int, comm: str, commDataTop: pd.DataFrame, cfg: dict):
        # prepare hover info
        hover = self._target == 'webapp'

        # individual lines
        costDataCorridor = {
            epdcase: commDataTop.query(f"epdcase=='{epdcase}' and impsubcase!='Case 1A'").sort_values(by='impcase')
            for epdcase in commDataTop['epdcase'].unique()
        }

        # middle line
        fig.add_trace(
            go.Scatter(
                x=costDataCorridor['medium']['impcase_x'],
                y=costDataCorridor['medium']['LCOP_rel'],
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
            row=1,
            col=c + 1,
        )

        # dashed middle line
        costDataDashed = commDataTop.query("epdcase=='medium' and impsubcase.isin(['Base Case', 'Case 1A'])")
        fig.add_trace(
            go.Scatter(
                x=[0.0, 0.9],
                y=costDataDashed['LCOP_rel'],
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
            row=1,
            col=c + 1,
        )

        # outside corridor
        fig.add_trace(
            go.Scatter(
                x=np.concatenate((costDataCorridor['strong']['impcase_x'][::-1], costDataCorridor['weak']['impcase_x'])),
                y=np.concatenate((costDataCorridor['strong']['LCOP_rel'][::-1], costDataCorridor['weak']['LCOP_rel'])),
                mode='lines',
                line=dict(
                    shape='spline',
                    width=0.0,
                ),
                fillcolor=("rgba({}, {}, {}, {})".format(*hex_to_rgb(cfg['globPlot']['commodity_colours'][comm]), .3)),
                fill='toself',
                showlegend=False,
                legendgroup=comm,
                hoverinfo='skip',
            ),
            row=1,
            col=c + 1
        )

        # points
        commDataTop = commDataTop.query(f"impcase!='Base Case' or epdcase=='medium'")
        for impsubcase in commDataTop['impsubcase'].unique():
            thisData = commDataTop.query(f"impsubcase=='{impsubcase}'")
            scatter = go.Scatter(
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
                    hovertemplate='<b>%{customdata[0]}</b><br>Elec.-price diff: %{customdata[1]}<br>Rel. prod. cost: %{y}%<extra></extra>',
                    customdata=thisData[['impsubcase', 'epd']] if hover else None,
                )
            fig.add_trace(
                scatter,
                row=1,
                col=c + 1,
            )

        # epd annotations
        epdLabel = commDataTop.query(f"impcase=='Case 3'")
        fig.add_trace(
            go.Scatter(
                x=epdLabel['impcase_x'],
                y=epdLabel['LCOP_rel'],
                text=epdLabel['epd'],
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
            row=1,
            col=c + 1,
        )

        # case annotation
        for impsubcase, epdcase, x, pos in [('Case 1A', 'weak', 0.9, 'middle left'), ('Case 1B', 'strong', 1.0, 'bottom right')]:
            caseLabel = commDataTop.query(f"impsubcase=='{impsubcase}' & epdcase=='{epdcase}'")
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
                row=1,
                col=c + 1,
            )

    def __addBottom(self, fig: go.Figure, c: int, comm: str, commDataBottom: pd.DataFrame, heatmap: dict, cfg: dict):
        # prepare hover info
        hover = self._target == 'webapp'

        # points
        for impsubcase in commDataBottom['impsubcase'].unique():
            if impsubcase == 'Base Case': continue
            thisData = commDataBottom.query(f"impsubcase=='{impsubcase}'")

            # add points
            fig.add_trace(
                go.Scatter(
                    x=-thisData['elec'],
                    y=thisData['other'],
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
                    hovertemplate='<b>%{customdata[0]}</b><br>Elec.-price diff: %{customdata[1]}<br>Energy-cost savings: %{x} EUR/t<br>Penalties: %{y} EUR/t<extra></extra>',
                    customdata=thisData[['impsubcase', 'epd']] if hover else None,
                ),
                row=2,
                col=c + 1,
            )

            # epd annotations
            epdLabel = thisData.query(f"impsubcase in ['Case 1A', 'Case 1B', 'Case 2']")
            fig.add_trace(
                go.Scatter(
                    x=-epdLabel['elec'],
                    y=epdLabel['other'],
                    text=epdLabel['epd'],
                    name=comm,
                    mode='markers+text',
                    textposition='bottom center',
                    textfont_size=self.getFontSize('fs_tn'),
                    textfont_color=cfg['globPlot']['commodity_colours'][comm],
                    marker_size=cfg['globStyle'][self._target]['marker_sm'],
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    legendgroup=comm,
                    hoverinfo='skip',
                ),
                row=2,
                col=c + 1,
            )

            # case annotations
            caseLabel = thisData.query(f"epdcase=='medium'")
            fig.add_trace(
                go.Scatter(
                    x=-caseLabel['elec'],
                    y=caseLabel['other'],
                    text=caseLabel['impsubcase'],
                    name=comm,
                    mode='markers+text',
                    textposition='top center',
                    textfont_size=self.getFontSize('fs_sm'),
                    textfont_color=cfg['globPlot']['commodity_colours'][comm],
                    marker_size=cfg['globStyle'][self._target]['marker_sm'],
                    marker_color='rgba(0,0,0,0)',
                    showlegend=False,
                    legendgroup=comm,
                    hoverinfo='skip',
                ),
                row=2,
                col=c + 1,
            )

        # heatmap
        colbarlen = 3/4 * cfg['bottom']['domain_boundary']
        fig.add_trace(
            go.Heatmap(
                x=heatmap['x'],
                y=heatmap['y'],
                z=heatmap['z'],
                zsmooth='best',
                zmin=cfg['bottom']['zrange'][0],
                zmax=cfg['bottom']['zrange'][1],
                colorscale=[
                    [i/(len(cfg['bottom']['zcolours'])-1), colour]
                    for i, colour in enumerate(cfg['bottom']['zcolours'])
                ],
                colorbar=dict(
                    x=1.01,
                    y=colbarlen/2,
                    yanchor='middle',
                    len=colbarlen,
                    title=cfg['bottom']['zaxislabel'],
                    titleside='right',
                    tickvals=[float(t) for t in cfg['bottom']['zticks']],
                    ticktext=cfg['bottom']['zticks'],
                    titlefont_size=self.getFontSize('fs_sm'),
                ),
                showscale=not c,
                hoverinfo='skip',
            ),
            row=2,
            col=c + 1,
        )

        # contour
        if cfg['contourLines']:
            fig.add_trace(
                go.Contour(
                    x=heatmap['x'],
                    y=heatmap['y'],
                    z=heatmap['z'],
                    contours_coloring='lines',
                    colorscale=[
                        [0.0, '#000000'],
                        [1.0, '#000000'],
                    ],
                    line_width=cfg['globStyle'][self._target]['lw_ultrathin']/2,
                    contours=dict(
                        showlabels=False,
                        start=cfg['bottom']['zrange'][0],
                        end=cfg['bottom']['zrange'][1],
                        size=10.0,
                    ),
                    showscale=False,
                    hoverinfo='skip',
                ),
                row=2,
                col=c + 1,
            )

        # add center line
        fig.add_trace(
            go.Scatter(
                x=[-1000.0, +10000.0],
                y=[-1000.0, +10000.0],
                mode='lines',
                line=dict(
                    color='black',
                    width=cfg['globStyle'][self._target]['lw_thin'],
                    dash='dash',
                ),
                showlegend=False,
                hoverinfo='skip',
            ),
            row=2,
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
            ay=0.18,
            axref=xref,
            ayref=yref,
            x=0.85,
            y=0.18,
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
            y=0.08,
            xref=xref,
            yref=yref,
        )

        fig.add_annotation(
            showarrow=True,
            text=None,
            ax=0.95,
            ay=0.8,
            axref=xref,
            ayref=yref,
            x=0.95,
            y=0.2,
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
            text='Increasing difference<br>of electricity prices',
            x=0.95,
            y=0.5,
            xref=xref,
            yref=yref,
            xanchor='center',
            yanchor='middle',
            textangle=270,
        )

        # bottom
        xref = f"x{c + 4} domain"
        yref = f"y{c + 4} domain"

        fig.add_annotation(
            showarrow=True,
            text=None,
            ax=0.65,
            ay=0.6,
            axref=xref,
            ayref=yref,
            x=0.9,
            y=0.35,
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
            text='Energy-cost savings prevail<br><br>Relocation is incentivised',
            x=0.8,
            y=0.45,
            xref=xref,
            yref=yref,
            xanchor='center',
            yanchor='middle',
            textangle=45,
        )

        fig.add_annotation(
            showarrow=True,
            text=None,
            ax=0.6,
            ay=0.65,
            axref=xref,
            ayref=yref,
            x=0.35,
            y=0.9,
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
            text='Penalties prevail<br><br>Relocation not incentivised',
            x=0.45,
            y=0.8,
            xref=xref,
            yref=yref,
            xanchor='center',
            yanchor='middle',
            textangle=45,
        )
