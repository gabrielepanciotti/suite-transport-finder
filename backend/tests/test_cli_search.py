"""Tests for the `tfind` multi-provider search CLI.

No network: the provider registry is swapped for stubs, so what is exercised here is the
part that is ours — parallel collection, failure degradation, ranking and rendering.
"""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from transportfinder_backend import cli, search
from transportfinder_backend.providers.base import Journey


def _journey(dep: str, arr: str, price: float | None, mode: str = "train", changes: int = 1):
    return Journey(
        provider="Stub",
        mode=mode,
        origin="Perugia",
        destination="Udine",
        departure=datetime.fromisoformat(dep),
        arrival=datetime.fromisoformat(arr),
        changes=changes,
        price=price,
        legs=["IC 580"],
    )


class _StubProvider:
    name = "Stub"

    def __init__(self, journeys=(), error: Exception | None = None):
        self._journeys = list(journeys)
        self._error = error

    def search(self, origin, destination, day, **kwargs):
        if self._error:
            raise self._error
        return self._journeys


def test_duration_is_derived_from_the_two_timestamps():
    j = _journey("2026-09-13T06:37", "2026-09-13T13:51", 55.75)
    assert j.duration_min == 434
    assert j.duration_hhmm == "7h14"


def test_duration_survives_an_overnight_arrival():
    j = _journey("2026-09-13T17:15", "2026-09-14T02:35", 59.48)
    assert j.duration_hhmm == "9h20"


def test_collect_degrades_instead_of_failing_when_one_provider_dies(monkeypatch):
    good = _journey("2026-09-13T06:37", "2026-09-13T13:51", 55.75)
    monkeypatch.setattr(
        search,
        "PROVIDERS",
        {"train": _StubProvider([good]), "bus": _StubProvider(error=RuntimeError("502"))},
    )
    journeys, errors = search.collect("Perugia", "Udine", date(2026, 9, 13), ["train", "bus"], time(5))
    assert journeys == [good]
    assert errors == ["Stub: 502"]


@pytest.mark.parametrize(
    ("sort", "expected_first"),
    [("price", 45.48), ("duration", 55.75), ("departure", 55.75)],
)
def test_sorting_keys_order_as_advertised(sort, expected_first):
    cheap_but_slow = _journey("2026-09-13T07:55", "2026-09-13T17:25", 45.48, mode="bus")
    fast_but_dear = _journey("2026-09-13T06:37", "2026-09-13T13:51", 55.75)
    ranked = sorted([cheap_but_slow, fast_but_dear], key=cli.SORTS[sort])
    assert ranked[0].price == expected_first


def test_journeys_without_a_price_rank_last_not_first():
    priced = _journey("2026-09-13T06:37", "2026-09-13T13:51", 55.75)
    unpriced = _journey("2026-09-13T07:00", "2026-09-13T14:00", None)
    assert sorted([unpriced, priced], key=cli.SORTS["price"])[0] is priced


def test_render_table_marks_an_arrival_on_the_following_day():
    table = cli.render_table([_journey("2026-09-13T17:15", "2026-09-14T02:35", 59.48, mode="bus")])
    assert "02:35+1" in table
    assert "59.48" in table


def test_main_reports_a_missing_route_with_a_nonzero_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(search, "PROVIDERS", {"train": _StubProvider([])})
    assert cli.main(["Perugia", "Udine", "2026-09-13", "--modes", "train"]) == 1
    assert "Nessuna opzione" in capsys.readouterr().out


class _Split:
    """Stands in for a combine.Combined row: same surface, plus a price breakdown."""

    def __init__(self, dep, arr, price, changes=1):
        self.departure = datetime.fromisoformat(dep)
        self.arrival = datetime.fromisoformat(arr)
        self.price = price
        self.changes = changes
        self.mode = "bus"
        self.legs = ["a", "b"]
        self.price_breakdown = "x + y"

    @property
    def duration_min(self):
        return round((self.arrival - self.departure).total_seconds() / 60)


def test_dedupe_drops_a_split_that_costs_more_than_the_same_ride_sold_whole():
    direct = _journey("2026-09-13T07:55", "2026-09-13T17:25", 45.48, mode="bus", changes=0)
    split = _Split("2026-09-13T07:55", "2026-09-13T17:25", 46.48)
    assert cli.dedupe([split, direct]) == [direct]


def test_dedupe_keeps_both_when_the_split_undercuts_the_single_ticket():
    """FlixBus sells this trip for 29.47; its two legs bought apart cost 20.96."""
    single = _journey("2026-09-13T07:00", "2026-09-13T12:55", 29.47, mode="bus", changes=1)
    split = _Split("2026-09-13T07:00", "2026-09-13T12:55", 20.96)
    kept = cli.dedupe([single, split])
    assert len(kept) == 2
    assert sorted(j.price for j in kept) == [20.96, 29.47]


def test_dedupe_keeps_the_cheaper_row_when_the_change_count_ties():
    dear = _journey("2026-09-13T07:55", "2026-09-13T17:25", 72.98, mode="bus", changes=1)
    cheap = _journey("2026-09-13T07:55", "2026-09-13T17:25", 38.98, mode="bus", changes=1)
    assert cli.dedupe([dear, cheap]) == [cheap]


def test_dedupe_leaves_genuinely_different_itineraries_alone():
    a = _journey("2026-09-13T07:55", "2026-09-13T17:25", 45.48)
    b = _journey("2026-09-13T09:55", "2026-09-13T18:00", 68.99)
    assert len(cli.dedupe([a, b])) == 2


def test_a_zero_priced_leg_is_never_treated_as_purchasable():
    """Trenitalia's Link feeders are priced 0.00 and sold only bundled — not a real leg."""
    from transportfinder_backend.providers import combine

    free_feeder = _journey("2026-09-13T15:20", "2026-09-13T17:35", 0.0, changes=0)
    real_leg = _journey("2026-09-13T13:41", "2026-09-13T15:48", 16.20, changes=0)
    assert not combine._purchasable(free_feeder)
    assert combine._purchasable(real_leg)
    assert not combine._purchasable(_journey("2026-09-13T13:41", "2026-09-13T15:48", None))


def test_flixbus_reports_the_checkout_price_not_the_pre_fee_one():
    """`total` hides the booking fee; only `total_with_platform_fee` matches the shop."""
    import inspect

    from transportfinder_backend.providers import flixbus

    src = inspect.getsource(flixbus.search)
    assert "total_with_platform_fee" in src
