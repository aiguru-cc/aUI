"""Value-driven native navigation using NavigationPath and NavigationLink."""

from dataclasses import dataclass

from aui import (
    Color, Form, NavigationBarTitleDisplayMode, NavigationLink, NavigationPath,
    NavigationStack, Size, Text, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


@dataclass(frozen=True)
class Article:
    title: str
    body: str


path = NavigationPath()
articles = [
    Article("Declarative views", "A view is a lightweight description of UI."),
    Article("Value navigation", "The path is the single source of navigation state."),
    Article("Native rendering", "AppKit maps descriptions to native Cocoa controls."),
]


def article_view(article: Article):
    return VStack([
        Text(article.title),
        Text(article.body),
        Text(f"Path depth: {len(path)}"),
    ], spacing=16, alignment="leading").padding(length=24).navigation_title(
        article.title
    ).navigation_bar_title_display_mode(
        NavigationBarTitleDisplayMode.LARGE
    ).navigation_bar_background(Color(0.93, 0.96, 1.0))


def make_view():
    root = Form([
        Text("Articles"),
        *[NavigationLink(article.title, article, path) for article in articles],
    ], spacing=12).padding(length=20).navigation_title("Articles")
    return NavigationStack(root, path=path).navigation_destination(
        Article, article_view
    )


def main():
    AppKitApplication(
        Window("aUI · NavigationPath", make_view, default_size=Size(620, 460))
    ).run()


if __name__ == "__main__":
    main()
