"""Select the exact retained movement represented by a lifecycle trade."""
def closing_movement(inputs,movement_key=None):
    movements=inputs.get('movements',[])
    if movement_key is None:
        if len(movements)!=1:raise ValueError('Multi-allocation closure requires an exact movement identity')
        return movements[0]
    matches=[m for m in movements if m.get('movementKey')==movement_key]
    if len(matches)!=1:raise ValueError('Missing or ambiguous maturity movement identity')
    return matches[0]
