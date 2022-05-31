
def queri_to_list(queri, column: str = None) -> list:
    list_of_items = []
    for item in queri:
        if column:
            list_of_items.append(str(item.__getattribute__(column)))
        else:
            list_of_items.append(str(item))
    return list_of_items
