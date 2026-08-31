"""Locale-aware SwiftUI-like FormatStyle values implemented in pure Python."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any, Iterable, Optional

from .localization import Locale


class FormatStyle:
    def format(self, value: Any, locale: Locale | str | None = None) -> str:
        raise NotImplementedError


class ParseableFormatStyle(FormatStyle):
    def parse(self, text: str, locale: Locale | str | None = None) -> Any:
        raise NotImplementedError


def _locale(locale): return locale if isinstance(locale, Locale) else Locale(str(locale or "en"))


@dataclass(frozen=True)
class NumberFormatStyle(ParseableFormatStyle):
    kind: str = "number"
    currency_code: str = "USD"
    minimum_fraction_digits: int = 0
    maximum_fraction_digits: int = 2
    uses_grouping: bool = True
    sign_strategy: str = "automatic"

    @classmethod
    def number(cls): return cls()
    @classmethod
    def percent(cls): return cls(kind="percent", maximum_fraction_digits=0)
    @classmethod
    def currency(cls, code: str = "USD"): return cls(kind="currency", currency_code=code.upper(), minimum_fraction_digits=2, maximum_fraction_digits=2)

    def precision(self, minimum: int = 0, maximum: Optional[int] = None):
        maximum = minimum if maximum is None else maximum
        if minimum < 0 or maximum < minimum: raise ValueError("invalid fraction precision")
        return replace(self, minimum_fraction_digits=minimum, maximum_fraction_digits=maximum)

    def grouping(self, enabled: bool = True): return replace(self, uses_grouping=bool(enabled))
    def sign(self, strategy: str):
        if strategy not in {"automatic", "always", "never"}: raise ValueError("invalid sign strategy")
        return replace(self, sign_strategy=strategy)

    def format(self, value, locale=None):
        locale = _locale(locale); number = float(value)
        if self.kind == "percent": number *= 100
        spec = f",.{self.maximum_fraction_digits}f" if self.uses_grouping else f".{self.maximum_fraction_digits}f"
        text = format(number, spec)
        if self.maximum_fraction_digits > self.minimum_fraction_digits and "." in text:
            whole, fraction = text.split(".")
            fraction = fraction.rstrip("0")
            fraction += "0" * max(0, self.minimum_fraction_digits - len(fraction))
            text = whole + (("." + fraction) if fraction else "")
        if self.sign_strategy == "always" and number >= 0: text = "+" + text
        if self.sign_strategy == "never": text = text.lstrip("+-")
        if locale.language_code in {"de", "fr", "es", "it", "pt"}:
            text = text.replace(",", "\0").replace(".", ",").replace("\0", ".")
        if self.kind == "percent": text += "%"
        elif self.kind == "currency":
            symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥"}
            symbol = symbols.get(self.currency_code, self.currency_code + " ")
            text = (text + " " + symbol) if locale.language_code in {"de", "fr"} else symbol + text
        return text

    def parse(self, text: str, locale=None):
        locale = _locale(locale); value = text.strip()
        for token in ("$", "€", "£", "¥", self.currency_code, "%", " "):
            value = value.replace(token, "")
        if locale.language_code in {"de", "fr", "es", "it", "pt"}:
            value = value.replace(".", "").replace(",", ".")
        else: value = value.replace(",", "")
        number = float(value)
        return number / 100 if self.kind == "percent" else number


@dataclass(frozen=True)
class DateFormatStyle(ParseableFormatStyle):
    date_style: str = "abbreviated"
    time_style: str = "omitted"

    def __post_init__(self):
        valid = {"omitted", "numeric", "abbreviated", "long", "complete", "short", "standard"}
        if self.date_style not in valid or self.time_style not in valid: raise ValueError("invalid date/time style")

    def format(self, value, locale=None):
        if not isinstance(value, (date, datetime)): raise TypeError("DateFormatStyle expects date or datetime")
        date_patterns = {"omitted": "", "numeric": "%Y-%m-%d", "abbreviated": "%b %d, %Y", "long": "%B %d, %Y", "complete": "%A, %B %d, %Y", "short": "%y-%m-%d", "standard": "%Y-%m-%d"}
        time_patterns = {"omitted": "", "short": "%H:%M", "standard": "%H:%M:%S", "numeric": "%H:%M", "abbreviated": "%H:%M", "long": "%H:%M:%S", "complete": "%H:%M:%S"}
        return " ".join(filter(None, [value.strftime(date_patterns[self.date_style]), value.strftime(time_patterns[self.time_style])]))

    def parse(self, text, locale=None):
        for pattern in ("%Y-%m-%d", "%y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
            try: return datetime.strptime(text.strip(), pattern)
            except ValueError: pass
        raise ValueError(f"cannot parse date: {text!r}")


@dataclass(frozen=True)
class ListFormatStyle(FormatStyle):
    conjunction: str = "and"

    def format(self, value: Iterable, locale=None):
        items = [str(item) for item in value]
        if len(items) < 2: return "".join(items)
        locale = _locale(locale)
        words = {"zh": "、", "ja": "、", "fr": " et ", "de": " und ", "en": f" {self.conjunction} "}
        joiner = words.get(locale.language_code, f" {self.conjunction} ")
        if locale.language_code in {"zh", "ja"}: return joiner.join(items)
        if len(items) == 2: return joiner.join(items)
        return ", ".join(items[:-1]) + "," + joiner + items[-1]


@dataclass(frozen=True)
class ByteCountFormatStyle(FormatStyle):
    binary: bool = False

    def format(self, value, locale=None):
        number = float(value); step = 1024.0 if self.binary else 1000.0
        units = ("B", "KiB", "MiB", "GiB", "TiB") if self.binary else ("B", "KB", "MB", "GB", "TB")
        index = 0
        while abs(number) >= step and index < len(units) - 1:
            number /= step; index += 1
        return f"{number:.0f} {units[index]}" if index == 0 else f"{number:.1f} {units[index]}"
