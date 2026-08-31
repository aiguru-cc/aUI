"""PreferenceKey upward data flow across a child view tree."""
from aui import PreferenceKey, State, Text, VStack, Window
from appkit_support import run_window


class HeightSummaryKey(PreferenceKey):
    default_value = 0

    @classmethod
    def reduce(cls, value, next_value):
        return value + next_value


total = State(0)


def content():
    rows = [
        Text(f"Row {index}").preference(HeightSummaryKey, index * 10)
        for index in range(1, 5)
    ]
    return VStack([
        Text(f"Child preference total: {total.wrapped_value}"),
        VStack(rows).transform_preference(HeightSummaryKey, lambda value: value + 5),
    ]).on_preference_change(HeightSummaryKey, total._set)


if __name__ == "__main__":
    run_window("PreferenceKey", content, width=500, height=320)
