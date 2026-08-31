from datetime import datetime

import pytest

from aui import (
    ByteCountFormatStyle, DateFormatStyle, ListFormatStyle, Locale,
    NumberFormatStyle, Text, VStack,
)
from aui.backends.ascii import AsciiBackend


def test_number_precision_grouping_and_sign():
    style = NumberFormatStyle.number().precision(1, 3).sign("always")
    assert style.format(1234.5) == "+1,234.5"
    assert style.grouping(False).format(1234.5) == "+1234.5"
    assert style.sign("never").format(-3.2) == "3.2"


def test_number_locale_separators_and_parse_roundtrip():
    style = NumberFormatStyle.number().precision(2)
    assert style.format(1234.5, Locale("de-DE")) == "1.234,50"
    assert style.parse("1.234,50", Locale("de-DE")) == pytest.approx(1234.5)
    assert style.parse("1,234.50", Locale("en-US")) == pytest.approx(1234.5)


def test_percent_and_currency_styles():
    percent = NumberFormatStyle.percent().precision(1)
    assert percent.format(0.256) == "25.6%"
    assert percent.parse("25.6%") == pytest.approx(0.256)
    assert NumberFormatStyle.currency("USD").format(12) == "$12.00"
    assert NumberFormatStyle.currency("EUR").format(12, "fr-FR") == "12,00 €"


def test_number_style_validation():
    with pytest.raises(ValueError): NumberFormatStyle.number().precision(3, 2)
    with pytest.raises(ValueError): NumberFormatStyle.number().sign("accounting")


def test_date_format_and_parse():
    value = datetime(2026, 8, 30, 14, 5, 9)
    assert DateFormatStyle("numeric", "short").format(value) == "2026-08-30 14:05"
    assert DateFormatStyle("long").format(value) == "August 30, 2026"
    assert DateFormatStyle("numeric").parse("2026-08-30").date() == value.date()
    with pytest.raises(ValueError): DateFormatStyle("invalid")


def test_list_format_locales():
    style = ListFormatStyle()
    assert style.format(["A", "B", "C"], "en") == "A, B, and C"
    assert style.format(["A", "B"], "de") == "A und B"
    assert style.format(["甲", "乙", "丙"], "zh") == "甲、乙、丙"


def test_byte_count_decimal_and_binary():
    assert ByteCountFormatStyle().format(1_500_000) == "1.5 MB"
    assert ByteCountFormatStyle(binary=True).format(1024) == "1.0 KiB"
    assert ByteCountFormatStyle().format(42) == "42 B"


def test_text_value_format_uses_environment_locale():
    view = VStack([
        Text(1234.5, format=NumberFormatStyle.number().precision(2)),
        Text(0.42, format=NumberFormatStyle.percent()),
    ]).locale("de-DE")
    output = AsciiBackend(30, 3).render(view)
    assert "1.234,50" in output
    assert "42%" in output


def test_text_rejects_non_format_style():
    with pytest.raises(TypeError): Text(12, format=".2f")
