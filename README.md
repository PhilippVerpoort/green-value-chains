# Research software used for techno-economic analysis of the impact of global heterogeneity of renewable energy supply on heavy industrial production and green value chains

## Summary
This repository make source codes and input data publicly available that were used in the analysis of the impact of global heterogeneity of renewable energy supply on heavy industrial production and green value chains in an accompanying research article and interactive webapp.

## How  to cite this work
**This software:**
Verpoort, Philipp C.; Gast, Lukas; Hofmann, A.; Ueckerdt, F. (2024): Research software used for techno-economic analysis of the impact of global heterogeneity of renewable energy supply on heavy industrial production and green value chains. V. 4.1.0. Zenodo. DOI: TBC

**The accompanying interactive webapp:**
Verpoort, Philipp C.; Gast, Lukas; Hofmann, Anke; Ueckerdt, Falko (2024): Interactive webapp for techno-economic analysis of green value chains. V. 4.1.0. GFZ Data Services. https://doi.org/10.5880/pik.2024.002

**The accompanying peer-reviewed article:**
Verpoort, Philipp C.; Gast, Lukas; Hofmann, A.; Ueckerdt, F. (2024): Impact of global heterogeneity of renewable-energy supply on heavy industrial production and green value chains. Nature Energy. DOI: TBC

## How to use this software

#### Run hosted service online:
This source code can be installed and executed to reproduce all the results (mainly figures) presented in the accompanying article and to run the interactive webapp. Note that the webapp is also hosted as a public service here: TBC

#### Install dependencies:
If you would like to try to execute this software locally on your machine, then you will need to have its Python dependencies installed.

The easiest way to accomplish this is via [poetry](https://python-poetry.org/):
```commandline
poetry install
```

Alternatively, you can install the required packages using `pip` (potentially following the creation of a virtual environment):

```commandline
pip install git+https://github.com/PhilippVerpoort/piw.git@v0.8.2
pip install git+https://github.com/PhilippVerpoort/posted.git@v0.2.3
pip install pandas openpyxl kaleido
```

#### Export figures manually
After activating the virtual environment (e.g. via `poetry shell`), please use:
```commandline
python export.py
```
This will export all figures. Alternatively, you may choose to export only Fig. 1 by using:
```commandline
python export.py fig1
```

#### Running the interactive webapp
The interactive webapp, which is also hosted here (TBC), can be run via: 
```commandline
python webapp.py
```
and then navigating to the provided IP address and port provided in your terminal, which is usually http://127.0.0.1:8050/.

## Licence
The source code in this repository is available under an [MIT Licence](https://opensource.org/licenses/MIT), a copy of which is also provided as a separate file in this repository.

## References
Verpoort, P. C. (2024). Potsdam Interactive Webapp (PIW) framework library (0.8.2). Zenodo. https://doi.org/10.5281/zenodo.10640781

Verpoort, P. C., Bachorz, C., Dürrwächter, J., Effing, P., Gast, L., Hofmann, A., & Ueckerdt, F. (2024). POSTED: Potsdam open-source techno-economic database (0.2.3). Zenodo. https://doi.org/10.5281/zenodo.10640888
