


def dummy_shuffle(distractors: list, row: dict, rng) -> list:
    """
    A dummy sorting method that simply shuffles the distractors randomly. This is used as a baseline to compare against
    more sophisticated sorting methods. It does not take into account the content of the distractors or the question.
    """

    # create a copy of the list to avoid modifying the original
    # import random

    distractors = distractors.copy()
    rng.shuffle(distractors)
    return distractors