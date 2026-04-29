# Short/Long Response Logic for Agent

import random

def respond_to_status_query(verbose_preference=None):
    """
    Returns a short or long response based on user preference or randomly.
    verbose_preference: True (always long), False (always short), None (random)
    """
    short_responses = ["Yes.", "Started.", "In progress.", "Done."]
    long_responses = [
        "Yes, I have started the task and am making progress.",
        "The task is underway and progressing as expected.",
        "I've begun working on it and will update you soon.",
        "Work has started and is ongoing."
    ]
    if verbose_preference is True:
        return random.choice(long_responses)
    if verbose_preference is False:
        return random.choice(short_responses)
    # Randomly choose
    if random.random() < 0.5:
        return random.choice(short_responses)
    else:
        return random.choice(long_responses)

# Example usage:
# print(respond_to_status_query())
# print(respond_to_status_query(verbose_preference=True))
# print(respond_to_status_query(verbose_preference=False))
