import pathlib


BASE_PATH = pathlib.Path(__file__).parent.parent.parent.parent.resolve()

def pathOfFile(dname, fname):
    return (BASE_PATH / dname / fname).resolve()

def pathOfAssetsFile(fname):
    return (BASE_PATH / 'assets'/ fname).resolve()

def pathOfConfigFile(fname):
    return (BASE_PATH / 'config' / fname).resolve()

def pathOfDataFile(fname):
    return (BASE_PATH / 'data' / fname).resolve()

def pathOfOutputFile(fname):
    return (BASE_PATH / 'output' / fname).resolve()
