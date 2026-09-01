# SwiftUI / Flet 对齐审计

更新时间：2026-09-01

## 结论

aUI 当前采用 SwiftUI 风格的声明式 View/Modifier/State API，并以 Flet 的跨平台实用性作为补充。内置后端为：

| 后端 | 平台 | 可用性 | 渲染模型 | 主要能力 |
| --- | --- | --- | --- | --- |
| `StandardBackend` | macOS/Linux/Windows | tkinter 可用时 | 原生桌面控件 + 增量 diff | toolbar、导航栏、分栏、文件对话框、Snackbar、动画 |
| `AppKitBackend` | macOS | PyObjC 可用时 | Cocoa 原生控件 | 原生符号、滚动、Toolbar、窗口场景 |
| `CursesBackend` | macOS/Linux/Windows* | curses 可用时 | 终端交互 | 键盘焦点、滚动、编辑、可访问性树 |
| `AsciiBackend` | 全平台 | 始终可用 | 无头确定性文本 | 预览、CI、快照、降级运行 |

`*` Windows 需要 `windows-curses`。
可通过 `python -m pip install -e '.[windows]'` 安装 Windows 终端支持。

## 已验证契约

- View 的 `size_that_fits` / `place` 布局协议和 `VStack`、`HStack`、`ZStack`、`Grid`、`NavigationSplitView`、响应式行布局。
- State、Binding、ObservableObject、Environment、观察追踪与后端关闭清理。
- 增量渲染、List 可视窗口虚拟化、稳定路径身份、动画帧驱动。
- SwiftUI 风格导航、Toolbar、窗口场景、Presentation、手势、键盘快捷键、Focus、可访问性和动态类型尺寸。
- `StandardTheme` / `AppKitTheme` 的颜色令牌及 `font_scale` 动态字体契约。
- 所有内置后端统一提供 `supports()`、`available()`、`availability_reason()`。

## 跨平台 CI 证据

`.github/workflows/test.yml` 覆盖 macOS、Ubuntu、Windows，以及 Python 3.10、3.12；Linux 使用 Xvfb，Windows 安装 `windows-curses`，并执行 StandardBackend 窗口创建/关闭烟测。最近一次运行（提交 `61a7060`）6 个矩阵任务全部成功。

本地全量回归：`707 passed, 7 skipped`。

`pyproject.toml` 已通过 Python `tomllib` 解析，`dev`、`appkit`、`windows`、`all`
extras 均存在。当前受限环境无法访问 PyPI，因而未执行隔离式 PEP 517 安装验证；
CI 会在各平台从干净环境执行安装。

## 明确边界

1. Qt 等额外 GUI 后端尚未实现；这不是当前内置 API 的隐式降级目标。
2. AppKit 的真实视觉效果仍需在 macOS 图形会话人工目检；离屏控件帧和越界断言已覆盖几何回归。
3. Curses 是终端语义，不宣称具备桌面 Toolbar、原生符号或可拖拽分隔线。
4. Flet 仅作为设计参考，不引入运行时依赖；aUI 保持标准库/可选 PyObjC 路线。

## 发布前检查

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src examples
git diff --check
```
