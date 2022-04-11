# simple update
def updateScenarioInputSimple(simple_gwp: str, simple_important_params: list):
    assumpts = {}

    # update gwp option
    assumpts['gwp'] = simple_gwp
    assumpts['share_secondary'] = 0.1

    # update important params
    for entry in simple_important_params:
        assumpts[entry['name']] = {2025: entry['val_2025'], 2050: entry['val_2050']}

    return assumpts
