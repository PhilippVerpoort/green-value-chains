import re

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_routes, all_processes


def plotValueCreation(costData: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataNew, order = __adjustData(costData, config) if subfigs_needed else (None, None)


    # produce figure
    ret['fig4'] = __produceFigure(costDataNew, order, config) if 'fig4' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, config: dict):
    # replace non-energy types with generic label
    if config['simplify_types']:
        mapping = {t: 'non-energy' for t in costData['type'] if t!='energy'}
        costDataNew = costData.replace({'type': mapping})
    else:
        costDataNew = costData


    # determine the route to plot for each commodity
    plottedRoutes = {
        c: costDataNew.query(f"commodity=='{c}' & case=='{config['import_route'][c]}'").route.iloc[0]
        for c in all_routes
    }


    # modify data for each commodity
    retData = []
    retOrder = {}
    for commodity, showRoute in plottedRoutes.items():
        # query relevant commodity data for given route
        costDataNewComm = costDataNew.query(f"route=='{showRoute}' & period=={config['show_year']}")\
                                     .drop(columns=['component', 'route', 'case', 'period'])

        # get processes in the route
        processes = all_routes[commodity][re.sub('--.*', '', showRoute)]['processes']
        processes_keys = list(processes.keys())

        # add upstream data for plotting
        for i, p in enumerate(processes_keys[:-1]):
            upstreamCostData = costDataNewComm.query(f"process=='{p}'").assign(type='upstream')
            costDataNewComm = pd.concat([costDataNewComm, upstreamCostData.assign(process=processes_keys[i+1])], ignore_index=True)

        # aggregate data over processes and types
        costDataNewComm = costDataNewComm.groupby(['commodity', 'process', 'type'])\
                                 .agg({'commodity': 'first', 'process': 'first', 'type': 'first', 'val': 'sum'})\
                                 .reset_index(drop=True)

        # add process labels
        costDataNewComm['process_label'] = [all_processes[p]['short'] for p in costDataNewComm['process']]

        # append data
        retData.append(costDataNewComm)

        # save list of processes, so they display in the correct order
        retOrder[commodity] = processes_keys


    return pd.concat(retData), retOrder


def __produceFigure(costData: pd.DataFrame, processesOrdered: dict, config: dict):
    commodities = costData.commodity.unique().tolist()


    # create figure
    hspcng = 0.04
    fig = make_subplots(
        cols=len(commodities),
        horizontal_spacing=hspcng,
    )


    # add bars for each subplot
    showTypes = [(t, d) for t, d in config['types'].items() if t in costData.type.unique()]
    hasLegend = []
    for i, c in enumerate(commodities):
        # plot data for commodity
        plotData = costData.query(f"commodity=='{c}'")


        # determine ymax
        ymax = 1.2 * plotData.query("type!='upstream'").val.sum()


        for j, p in enumerate(processesOrdered[c]):
            # plot data for individual process
            plotDataProc = plotData.query(f"process=='{p}'")


            # determine spacing of pie charts
            w1 = (1.0 - hspcng*(len(commodities)-1))/len(commodities)
            w2 = w1/len(processesOrdered[c])

            size = 0.10
            spacing = 0.04

            xstart = i * (w1+hspcng) + j * w2
            xend = i * (w1 + hspcng) + (j+1) * w2
            ypos = plotDataProc.val.sum()/ymax + size/2 + spacing


            # add pie charts
            plotDataPie = plotDataProc.query(f"type!='upstream'")
            fig.add_trace(go.Pie(
                labels=plotDataPie.replace({'type': {t: d['label'] for t,d in showTypes}}).type,
                values=plotDataPie.val,
                marker_colors=plotDataPie.replace({'type': {t: d['colour'] for t,d in showTypes}}).type,
                hovertemplate=f"<b>{all_processes[p]['label']}</b><br>%{{label}}<extra></extra>",
                showlegend=False,
                domain=dict(
                    x=[xstart, xend],
                    y=[ypos-size/2, ypos+size/2],
                ),
            ))

            # add bar charts
            base = 0.0
            for type, display in showTypes:
                plotDataProcType = plotDataProc.query(f"type=='{type}'")
                addHeight = plotDataProcType.val.sum()

                if type == 'upstream' and p in config['skip_upstream']:
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
                    col=i+1,
                )

                base += addHeight

                if type not in hasLegend:
                    hasLegend.append(type)


        # add annotations
        fig.add_annotation(
            text=f"<b>{c}</b>",
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
            col=i+1,
        )


        # update layout of subplot
        fig.update_layout(
            **{
                f"xaxis{i+1 if i else ''}": dict(title='', categoryorder='array', categoryarray=[all_processes[p]['short'] for p in processesOrdered[c] if p in plotData.process.unique()]),
                f"yaxis{i+1 if i else ''}": dict(title='', range=[0.0, ymax]),
            },
        )


    # update layout of all plots
    fig.update_layout(
        barmode='stack',
        yaxis=dict(title=config['yaxislabel']),
        legend_title='',
    )


    return fig
