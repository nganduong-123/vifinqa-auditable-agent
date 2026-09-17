"""Unit tests for period parsing."""

from vifinqa.semantic_parser import parse_periods, PeriodRef

def test_parse_single_year():
    periods = parse_periods("Doanh thu của FPT năm 2023")
    assert len(periods) == 1
    assert periods[0].year == 2023

def test_parse_two_years():
    periods = parse_periods("So sánh doanh thu FPT năm 2022 và 2023")
    assert len(periods) == 2
    assert periods[0].year == 2022
    assert periods[1].year == 2023
    assert all(period.is_comparative for period in periods)


def test_parse_year_range():
    periods = parse_periods("Lợi nhuận FPT giai đoạn 2019–2023")
    assert [period.year for period in periods] == [2019, 2020, 2021, 2022, 2023]
