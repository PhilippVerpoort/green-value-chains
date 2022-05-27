import yaml

from src.load.file_paths import getFilePathInput


def loadYamlFile(fname: str):
    __filePath = getFilePathInput(fname)
    return yaml.load(open(__filePath, 'r').read(), Loader=yaml.FullLoader)
