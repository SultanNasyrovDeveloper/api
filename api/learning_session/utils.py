from itertools import batched
from random import shuffle as random_shuffle


def shuffle[ItemType: int | str](array: list[ItemType]) -> list[ItemType]:
    shuffled_array = []
    for batch in batched(array, len(array) // 10 or 1):
        batch_as_list = list(batch)
        random_shuffle(batch_as_list)
        shuffled_array.extend(batch_as_list)
    return shuffled_array
