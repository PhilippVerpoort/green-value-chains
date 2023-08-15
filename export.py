import sys

from webapp import webapp


# get list of figs to plot from command line args and call webapp.export()
def export():
    if len(sys.argv) > 1:
        figNames = sys.argv[1:]
    else:
        figNames = None

    webapp.export(figNames, formats=['png', 'svg'])


if __name__ == '__main__':
    export()
