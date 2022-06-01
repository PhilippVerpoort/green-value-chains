import pandas as pd
import plotly.graph_objects as go

from src.plotting.styling.styling import defaultStyling


def plotLCOS(costData: pd.DataFrame, config: dict):
    # make adjustments to data
    costDataNew = __adjustData(costData, config)

    # produce figure
    fig = __produceFigure(costDataNew, config)

    # styling figure
    defaultStyling(fig)
    __styling(fig)

    return {'fig1': fig}


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    routes = costData['route'].unique()
    years = costData['val_year'].unique()

    # remove upstream cost entries
    costDataNew = costData.copy().query(f"type!='upstream'")

    # rename iron feedstock entries
    costDataNew.loc[(costDataNew['type'] == 'feedstock') & costDataNew['component'].isin(['ore', 'scrap']), 'type'] = 'iron'

    # load route names from plot config
    costDataNew.replace(config['route_names'], inplace=True)
    dummyData = pd.DataFrame.from_records([{'route': config['route_names'][r], 'type': 'dummy', 'val': 0.0, 'val_year': y}
                                           for r in sorted(list(routes), key=lambda x: list(config['route_names']).index(x)) for y in years])

    # costDataNew.loc[costDataNew['type'] == 'capital', 'hoverlabel'] = \
    #     [config['process_names'][p] for p in costDataNew.loc[costDataNew['type'] == 'capital', 'process']]
    # costDataNew.loc[costDataNew['type'] == 'energy', 'hoverlabel'] = \
    #     [config['process_names'][p] for p in costDataNew.loc[costDataNew['type'] == 'capital', 'process']]

    # determine breakdown level of bars and associated hover labels
    if config['full_breakdown'] == 'process':
        group_cols = ['type', 'val_year', 'route', 'process']
        costDataNew = costDataNew.groupby(group_cols).sum().reset_index()
        costDataNew['hover_label'] = [config['process_names'][p] for p in costDataNew['process']]
    elif config['full_breakdown'] == 'component':
        group_cols = ['type', 'val_year', 'route', 'component']
        costDataNew = costDataNew.fillna({'component': 'empty'}).groupby(group_cols).sum().reset_index()
        costDataNew['hover_label'] = [config['component_labels'][c] if c!='empty' else None for c in costDataNew['component']]
    elif config['full_breakdown'] == 'none':
        group_cols = ['type', 'val_year', 'route']
        costDataNew = costDataNew.groupby(group_cols).sum().reset_index()
    else:
        raise Exception('Value of config parameter full_breakdown is invalid.')

    return pd.concat([costDataNew, dummyData])


def __produceFigure(costData: pd.DataFrame, config: dict):
    # create figure
    fig = go.Figure()

    # add dummy entries such that the order is correct
    dummyData = costData.query(f"type=='dummy'")
    fig.add_trace(go.Bar(
        x=[dummyData.val_year, dummyData.route],
        y=dummyData.val,
        showlegend=False,
    ))

    # add traces for all cost types
    keys = config['labels'].keys()
    for stack in keys:
        plotData = costData.query(f"type=='{stack}'")
        hoverLabel = 'hover_label' in plotData.columns and any(plotData.hover_label.unique())

        fig.add_trace(go.Bar(
            x=[plotData.val_year, plotData.route],
            y=plotData.val,
            marker_color=config['colours'][stack],
            name=config['labels'][stack],
            customdata=plotData.hover_label if hoverLabel else None,
            hovertemplate=f"<b>{config['labels'][stack]}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>LCoS: %{{y}} EUR/t<extra></extra>",
        ))

    # add vertical line
    nYears = costData['val_year'].nunique()
    nRoutes = costData['route'].nunique()
    for i in range(nYears-1):
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


def __styling(fig: go.Figure):
    # update axis styling
    for axis in ['xaxis', 'yaxis']:
        update = {axis: dict(
            showline=True,
            linewidth=2,
            linecolor='black',
            showgrid=False,
            zeroline=False,
            mirror=True,
            ticks='outside',
        )}
        fig.update_layout(**update)
