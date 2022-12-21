from string import ascii_lowercase

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_processes, all_routes
from src.plotting.helperFuncs import groupbySumval


def plotLevelisedCost(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataAggregated, routeorder, costDataH2Transp = __adjustData(costData, config) if any(fName in subfigs_needed for fName in ['fig3', 'figS1a', 'figS1b', 'figS1c', 'figS3']) else (None, None, None)
    costDataRecAggregated, _, costDataRecH2Transp = __adjustData(costDataRec, config) if 'figS3' in subfigs_needed else (None, None, None)


    # produce fig1
    ret['fig3'] = __produceFigure(costDataAggregated, routeorder, costDataH2Transp, config, show_costdiff=not is_webapp) if 'fig3' in subfigs_needed else None


    # produce figS1
    for k, commodity in enumerate(list(all_routes.keys())):
        subfigName = f"figS1{ascii_lowercase[k]}"
        ret[subfigName] = __produceFigure(costDataAggregated, routeorder, costDataH2Transp, config, commodity=commodity) if subfigName in subfigs_needed else None


    # produce figS2
    ret['figS3'] = __produceFigure(costDataRecAggregated, routeorder, costDataRecH2Transp, config) if 'figS3' in subfigs_needed else None


    return ret


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    showRoutes = costData['route'].unique()
    showYears = costData['val_year'].unique()

    # remove upstream cost entries
    costDataNew = costData.copy().query(f"type!='upstream'")

    # split up hydrogen transport cost
    q = "type=='transport' and component=='hydrogen'"
    costDataH2Transp = costDataNew.query(q).reset_index(drop=True)
    costDataNew = costDataNew.query(f"not ({q})").reset_index(drop=True)
    costDataH2Transp['hover_label'] = 'Transport'

    # rename iron feedstock entries
    costDataNew.loc[(costDataNew['type'] == 'feedstock') & costDataNew['component'].isin(['ore', 'scrap']), 'type'] = 'iron'

    # define route names and ordering
    route_names_woimp = {route_id: route_vals['name'] for route_details in all_routes.values() for route_id, route_vals in sorted(route_details.items()) if route_id in costDataNew['route'].unique()}
    route_names_wiimp = {route_id: route_id.split('--')[-1] for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
    route_names = {**route_names_woimp, **route_names_wiimp}

    # rename routes into something readable
    costDataNew.replace({'route': route_names}, inplace=True)
    costDataH2Transp.replace({'route': route_names}, inplace=True)

    # determine breakdown level of bars and associated hover labels
    if config['aggregate_by'] == 'none':
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'subcomponent':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route', 'process', 'component'], keep=['case'])
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'component':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route', 'process'], keep=['case'])
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
    elif config['aggregate_by'] == 'process':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route', 'component'], keep=['case'])
        costDataNew['hover_label'] = [config['components'][c] if c!='empty' else None for c in costDataNew['component']]
    elif config['aggregate_by'] == 'all':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route'], keep=['case'])
        costDataNew['hover_label'] = [config['types'][t]['label'] for t in costDataNew['type']]
    else:
        raise Exception('Value of aggregate_by in the plot config is invalid.')

    # sort by commodities
    commodityOrder = costData.commodity.unique().tolist()
    costDataNew.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)

    # sort routes
    routeorder = [r.replace('Case 1A', 'Case 1A/B') for r in route_names.values() if r != 'Case 1B']

    return costDataNew, routeorder, costDataH2Transp


def __produceFigure(costData: pd.DataFrame, routeorder: list, costDataH2Transp: pd.DataFrame, config: dict, commodity: str = '', show_costdiff: bool = False):
    if commodity:
        q = f"commodity=='{commodity}'"
        costData = costData.query(q)
        costDataH2Transp = costDataH2Transp.query(q)
        subplots = [int(y) for y in sorted(costData.val_year.unique())]
    else:
        q = f"val_year=={config['show_year']} & case.notnull()"
        costData = costData.query(q)
        costDataH2Transp = costDataH2Transp.query(q)
        subplots = costData.commodity.unique().tolist()


    # create figure
    fig = make_subplots(
        cols=len(subplots),
        horizontal_spacing=0.05,
    )


    # add bars for each subplot
    for i, subplot in enumerate(subplots):
        ymax = addBars(commodity, config, costData, costDataH2Transp, fig, i, routeorder, subplot)

        # add cost differences from Base Case
        if show_costdiff:
            addCostDiff(commodity, config, costData, costDataH2Transp, fig, i, subplot, ymax)

    # update layout of all plots
    fig.update_layout(
        barmode='stack',
        yaxis_title=config['yaxislabel'],
        legend_title='',
    )


    return fig


def addBars(commodity, config, costData, costDataH2Transp, fig, i, routeorder, subplot):
    # select data for each subplot
    plotData = costData \
        .query(f"val_year=={subplot}" if commodity else f"commodity=='{subplot}'") \
        .query("case!='Case 1B'") \
        .replace({'route': 'Case 1A'}, 'Case 1A/B')
    plotDataH2Transp = costDataH2Transp.query(f"val_year=={subplot}" if commodity else f"commodity=='{subplot}'") \
        .replace({'route': ['Case 1A', 'Case 1B']}, 'Case 1A/B')

    # determine ymax
    if config['ymaxcalc']:
        ymax = 1.15 * plotData.query("route=='Base Case'").val.sum()
    else:
        ymax = config['ymax'][commodity] if commodity else config['ymax'][subplot]

    # whether a hover label should be set
    hoverLabel = 'hover_label' in plotData.columns and any(plotData.hover_label.unique())

    # add traces for all cost types
    for type, display in config['types'].items():
        thisData = plotData.query(f"type=='{type}'")

        fig.add_trace(
            go.Bar(
                x=thisData.route,
                y=thisData.val,
                marker_color=display['colour'],
                name=display['label'],
                customdata=thisData.hover_label if hoverLabel else None,
                showlegend=not i,
                hovertemplate=f"<b>{display['label']}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>Cost: %{{y}} EUR/t<extra></extra>",
                width=0.8,
            ),
            row=1,
            col=i + 1,
        )

    display = config['types']['transport']
    baseVal = plotData.query(f"route=='Case 1A/B'").val.sum()

    for m, c in enumerate(plotDataH2Transp.case.unique()):
        p = plotDataH2Transp.query(f"case=='{c}'")

        fig.add_trace(
            go.Bar(
                x=p.route,
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
            col=i + 1,
        )

    # add annotations
    fig.add_annotation(
        text=f"<b>{subplot}</b>",
        x=0.0,
        xref='x domain',
        xanchor='left',
        y=1.0,
        yref='y domain',
        yanchor='top',
        showarrow=False,
        bordercolor='black',
        borderwidth=2,
        borderpad=3,
        bgcolor='white',
        row=1,
        col=i + 1,
    )

    # update layout of subplot
    fig.update_layout(
        **{
            f"xaxis{i + 1 if i else ''}": dict(title='', categoryorder='array',
                                               categoryarray=[r for r in routeorder if r in plotData.route.unique()]),
            f"yaxis{i + 1 if i else ''}": dict(title='', range=[0.0, ymax]),
        },
    )

    return ymax


def addCostDiff(commodity, config, costData, costDataH2Transp, fig, i, subplot, ymax):
    correction = 0.018
    xshift = 2.5
    yshift = 35.0

    # select data for each subplot
    plotData = pd.concat([costData, costDataH2Transp]).query(
        f"val_year=={subplot}" if commodity else f"commodity=='{subplot}'")
    baseCost = plotData.query("route=='Base Case'").val.sum()

    fig.add_hline(
        baseCost,
        line_color='black',
        line_width=config['global']['lw_thin'],
        row=1,
        col=i + 1,
    )

    for j, route in enumerate(sorted(plotData.route.unique().tolist())[1:]):
        thisCost = plotData.query(f"route=='{route}'").val.sum()

        costDiff = thisCost - baseCost
        costDiffAbs = abs(costDiff)
        costDiffSign = '+' if costDiff > 0.0 else '-'

        if route == 'Case 1A':
            j -= 0.2
        elif route == 'Case 1B':
            j += 0.2
            j -= 1
        if j > 1:
            j -= 1

        fig.add_annotation(
            x=j + 1,
            y=min(thisCost, ymax),
            yref=f"y{i + 1 if i else ''}",
            ax=j + 1,
            ay=baseCost + (correction * ymax if costDiff < 0.0 else -correction * ymax),
            ayref=f"y{i + 1 if i else ''}",
            arrowcolor='black',
            arrowwidth=config['global']['lw_thin'],
            arrowhead=2,
            row=1,
            col=i + 1,
        )

        y = thisCost + (costDiffAbs / 2 if costDiff < 0.0 else -costDiffAbs / 2)
        if i==1 and route == 'Case 1A':
            y = thisCost - 3/4*costDiffAbs
        fig.add_annotation(
            text=f" {costDiffSign}{costDiffAbs:.2f}<br>({costDiffSign}{costDiffAbs / baseCost * 100:.2f}%)",
            align='left',
            showarrow=False,
            x=j + 1,
            xanchor='left',
            xshift=xshift,
            y=baseCost,
            yref=f"y{i + 1 if i else ''}",
            yanchor='middle',
            yshift=-yshift if costDiff < 0.0 else +yshift,
            row=1,
            col=i + 1,
        )
