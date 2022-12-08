import pandas as pd


def groupbySumval(df: pd.DataFrame, groupCols: list, keep: list = []):
    return df.groupby(groupCols) \
             .agg(dict(**{c: 'first' for c in groupCols+keep}, val='sum')) \
             .reset_index(drop=True)
