import pandas as pd
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb

from src.scaffolding.plotting.AbstractPlot import AbstractPlot


class BasePlot(AbstractPlot):
    def _getEpdCases(self):
        return self._inputData['elec_prices'].epdcase.unique()

    def _finaliseCostData(self, costData: pd.DataFrame, epdcases: list = None, epperiod: int = None):
        finalElecPrices = self._inputData['elec_prices'] \
            .query((f"epdcase in @epdcases" if epdcases else 'True') + ' and ' + (f"period=={epperiod}" if epperiod else 'True')) \
            .filter(['epdcase', 'location', 'val'] + (['period'] if not epperiod else []))

        elecPriceDiffs = pd.merge(
                finalElecPrices.query("location=='importer'"),
                finalElecPrices.query("location=='exporter'"),
                on=['epdcase'] + (['period'] if not epperiod else []),
                how='outer',
                suffixes=('_importer', '_exporter'),
            )\
            .assign(epdiff=lambda x: x.val_importer-x.val_exporter)\
            .filter(['epdcase', 'epdiff'] + (['period'] if not epperiod else []))

        q = f"type=='energy' and component=='electricity'"

        return pd.concat(
                [
                    costData \
                        .query(f"not ({q})") \
                        .merge(elecPriceDiffs, how='outer' if not epperiod else 'cross', on=['period'] if not epperiod else None),
                    costData \
                        .query(q) \
                        .merge(finalElecPrices, on=['location'] + (['period'] if not epperiod else []), how='outer') \
                        .assign(val=lambda x: x.val_x * x.val_y) \
                        .drop(columns=['val_x', 'val_y']) \
                        .merge(elecPriceDiffs, how='outer', on=['epdcase'] + (['period'] if not epperiod else [])),
                ]
            )\
            .reset_index(drop=True)

    @staticmethod
    def _groupbySumval(df: pd.DataFrame, groupCols: list, keep: list = []):
        if 'val_rel' in df.columns:
            raise Exception('Cannot sum relative values.')
        sumCols = [col for col in ['val', 'val_diff'] if col in df.columns]
        return df.groupby(groupCols) \
            .agg(dict(**{c: 'first' for c in groupCols + keep}, **{c: 'sum' for c in sumCols})) \
            .reset_index(drop=True)

    def _addAnnotation(self, fig: go.Figure, col: int, text: str, row: int = 1):
        fig.add_annotation(
            text=f"<b>{text}</b>",
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
            row=row,
            col=col + 1,
        )

    def _addAnnotationComm(self, fig: go.Figure, col: int, comm: str):
        fig.add_annotation(
            text=f"<b>{comm}</b>",
            x=0.5,
            xref='x domain',
            xanchor='center',
            y=1.0,
            yshift=30.0,
            yref='y domain',
            yanchor='bottom',
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=8,
            bgcolor="rgba({}, {}, {}, {})".format(*hex_to_rgb(self._config['commodity_colours'][comm]), .3),
            row=1,
            col=col + 1,
        )


    @staticmethod
    def _updateAxisLayout(fig: go.Figure, i: int, xaxis: dict = {}, yaxis: dict = {}):
        fig.update_layout(**{
            f"xaxis{i + 1 if i else ''}": xaxis,
            f"yaxis{i + 1 if i else ''}": yaxis,
        })
