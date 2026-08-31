import threading

import pytest

from aui import Grid, GridRow, Size, View
from aui.core.measurement import MeasurementCache, measure, measurement_context


class CountingView(View):
    def __init__(self):
        self.calls = 0

    def size_that_fits(self, proposal):
        self.calls += 1
        return Size(proposal.width / 2, 24)


def test_measurement_cache_keys_by_view_and_exact_proposal():
    cache = MeasurementCache()
    view = CountingView()
    assert cache.measure(view, Size(200, 100)) == Size(100, 24)
    assert cache.measure(view, Size(200, 100)) == Size(100, 24)
    assert cache.measure(view, Size(300, 100)) == Size(150, 24)
    assert view.calls == 2
    assert (cache.hits, cache.misses, len(cache)) == (1, 2, 2)


def test_clear_starts_a_fresh_layout_pass():
    cache = MeasurementCache()
    view = CountingView()
    cache.measure(view, Size(100, 100))
    cache.clear()
    cache.measure(view, Size(100, 100))
    assert view.calls == 2
    assert (cache.hits, cache.misses) == (0, 1)


def test_measurement_cache_rejects_invalid_view_result():
    view = CountingView()
    view.size_that_fits = lambda _proposal: (10, 20)
    with pytest.raises(TypeError, match="return Size"):
        MeasurementCache().measure(view, Size(100, 100))


def test_measurement_cache_is_safe_for_parallel_reads():
    cache = MeasurementCache()
    view = CountingView()
    values = []
    workers = [threading.Thread(target=lambda: values.append(
        cache.measure(view, Size(100, 100)))) for _ in range(8)]
    for worker in workers: worker.start()
    for worker in workers: worker.join()
    assert values == [Size(50, 24)] * 8
    assert view.calls == 1
    assert (cache.hits, cache.misses) == (7, 1)


def test_grid_internal_measurements_share_current_layout_context():
    first, second = CountingView(), CountingView()
    grid = Grid([GridRow([first, second])])
    cache = MeasurementCache()
    with measurement_context(cache):
        grid.metrics(Size(400, 200))
        grid.metrics(Size(400, 200))
    assert first.calls == second.calls == 1
    assert cache.hits == 2


def test_measure_falls_back_after_context_exits():
    view = CountingView()
    cache = MeasurementCache()
    with measurement_context(cache):
        measure(view, Size(100, 100))
        measure(view, Size(100, 100))
    measure(view, Size(100, 100))
    assert view.calls == 2


def test_measurement_stats_are_immutable_and_report_hit_rate():
    cache = MeasurementCache()
    view = CountingView()
    cache.measure(view, Size(100, 100))
    cache.measure(view, Size(100, 100))
    stats = cache.stats
    assert (stats.entries, stats.hits, stats.misses) == (1, 1, 1)
    assert stats.hit_rate == 0.5
    cache.clear()
    assert stats.entries == 1
    assert cache.stats.hit_rate == 0.0
