import re
from string import ascii_lowercase

import pandas as pd
import plotly.graph_objects as go

from src.load.load_default_data import all_processes, all_routes


def plotLevelisedCost(costData: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataAggregated = __adjustData(costData, config) if subfigs_needed else None


    # produce fig1
    ret['fig1'] = __produceFigure(costDataAggregated, config) if 'fig1' in subfigs_needed else None


    # produce SI figs
    subfigs = []
    for k, commodity in enumerate(list(all_routes.keys())):
        subfigName = f"figS1{ascii_lowercase[k]}"
        ret[subfigName] = __produceFigure(costDataAggregated, config, commodity=commodity) if subfigName in subfigs_needed else None


    return ret


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    showRoutes = costData['route'].unique()
    showYears = costData['val_year'].unique()

    # remove upstream cost entries
    costDataNew = costData.copy().query(f"type!='upstream'")

    # rename iron feedstock entries
    costDataNew.loc[(costDataNew['type'] == 'feedstock') & costDataNew['component'].isin(['ore', 'scrap']), 'type'] = 'iron'

    # define route names and ordering
    route_names_woimp = {route_id: route_vals['name'] for route_details in all_routes.values() for route_id, route_vals in sorted(route_details.items()) if route_id in costDataNew['route'].unique()}
    route_names_wiimp = {route_id: f"Case {route_id.split('_')[-1]}" for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
    route_names = {**route_names_woimp, **route_names_wiimp}

    # replace route names and add dummy data to force correct ordering
    costDataNew.replace({'route': route_names}, inplace=True)
    dummyData = pd.DataFrame.from_records([{'commodity': pg, 'route': route_names[r], 'type': 'dummy', 'val': 0.0, 'val_year': y}
                                           for r in route_names for y in showYears for pg in costData['commodity'].unique() if re.sub(r'_\d+$', '', r) in all_routes[pg]])

    # determine breakdown level of bars and associated hover labels
    if config['aggregate_by'] in ['none', 'subcomponent']:
        if config['aggregate_by'] == 'subcomponent':
            group_cols = ['type', 'val_year', 'commodity', 'route', 'process', 'component']
            costDataNew = costDataNew.fillna({'component': 'empty'}) \
                                     .groupby(group_cols).sum() \
                                     .sort_values('process', key=lambda col: [list(all_processes.keys()).index(p) for p in col]) \
                                     .reset_index()
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'component':
        group_cols = ['type', 'val_year', 'commodity', 'route', 'process']
        costDataNew = costDataNew.groupby(group_cols).sum() \
                                 .sort_values('process', key=lambda col: [list(all_processes.keys()).index(p) for p in col]) \
                                 .reset_index()
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
    elif config['aggregate_by'] == 'process':
        group_cols = ['type', 'val_year', 'commodity', 'route', 'component']

        costDataNew = costDataNew.fillna({'component': 'empty'}) \
                                 .groupby(group_cols).sum() \
                                 .sort_values('component', key=lambda col: [list(config['components']).index(c) if c!='empty' else -1 for c in col]) \
                                 .reset_index()
        costDataNew['hover_label'] = [config['components'][c] if c!='empty' else None for c in costDataNew['component']]
    elif config['aggregate_by'] == 'all':
        group_cols = ['type', 'val_year', 'commodity', 'route']
        costDataNew = costDataNew.groupby(group_cols).sum().reset_index()
    else:
        raise Exception('Value of aggregate_by in the plot config is invalid.')

    return pd.concat([costDataNew, dummyData])


def __produceFigure(costData: pd.DataFrame, config: dict, commodity: str = ''):
    if commodity:
        costData = costData.query(f"commodity=='{commodity}'")
    else:
        costData = costData.query(f"val_year=={config['show_year']} & route.str.startswith('Case')")


    # create figure
    fig = go.Figure()


    # add dummy entries such that the order is correct
    dummyData = costData.query(f"type=='dummy'")
    fig.add_trace(go.Bar(
        x=[dummyData.val_year, dummyData.route] if commodity else [dummyData.commodity, dummyData.route],
        y=dummyData.val,
        showlegend=False,
    ))


    # add traces for all cost types
    for type, display in config['types'].items():
        plotData = costData.query(f"type=='{type}'")
        hoverLabel = 'hover_label' in plotData.columns and any(plotData.hover_label.unique())

        fig.add_trace(go.Bar(
            x=[plotData.val_year, plotData.route] if commodity else [plotData.commodity, plotData.route],
            y=plotData.val,
            marker_color=display['colour'],
            name=display['label'],
            customdata=plotData.hover_label if hoverLabel else None,
            hovertemplate=f"<b>{display['label']}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>Cost: %{{y}} EUR/t<extra></extra>",
        ))


    # add vertical lines
    if commodity:
        nY = costData.val_year.nunique()
        for i, y in enumerate(sorted(costData.val_year.unique())):
            if i+1 == nY: continue
            nRoutes = costData.query(f"val_year=={y}").route.nunique()
            fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')
            fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')
    else:
        nC = costData.commodity.nunique()
        for i, c in enumerate(costData.commodity.unique()):
            if i+1 == nC: continue
            nRoutes = costData.query(f"commodity=='{c}'").route.nunique()
            fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')
            fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')


    # set axes labels
    fig.update_layout(
        barmode='stack',
        xaxis=dict(title=''),
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        legend_title=''
    )

    return fig
