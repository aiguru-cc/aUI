# ADR-0004: 后端选型 — curses（零依赖默认）+ AppKit（macOS 原生窗口）

- 状态：已接受（2026-08-28 修订：移除 Tk，新增 AppKit）
- 日期：2026-08-26

## 背景

Tkinter 后端在目标开发机（Homebrew Python 3.14）上不可用——该解释器未编译
`_tkinter` 模块。需要评估“不用 Tk 支持、Python 原生编写”的替代路径。

## 备选方案

1. **curses 终端 UI**：标准库自带，零依赖，跨平台，当前环境直接可用。
2. **AppKit/Cocoa 窗口**（PyObjC 调系统图形框架）：macOS 上真正的原生窗口，
   每个组件映射为原生 `NSControl`；需安装 `pyobjc-framework-Cocoa`。
3. **自绘 GUI**（ctypes 调系统图形 API）：无官方 Python 绑定，需自实现窗口/
   事件/绘制/文本渲染，数周工作量，平台绑定严重。
4. **Web 后端**（http.server + 浏览器）：外观现代但需 HTML/JS 桥接层，
   引入异步通信复杂度，3–5 天工作量。
5. **修复 Tk**（`brew install python-tk`）：只解决单机问题，仍受 Tk 8.5 限制。

## 决策

采用 **curses 终端后端**（`src/aui/backends/curses.py`）作为 aUI 默认的
零依赖原生交互后端，并**移除 Tkinter 后端**（`src/aui/backends/tk.py` 及其示例、
测试已删除）。

同时新增 **AppKit 后端**（`src/aui/backends/appkit.py`）作为 macOS 的
**原生窗口**后端：通过 PyObjC 直接调用 Cocoa 框架（SwiftUI 在 macOS 上底层
就是 AppKit），组件映射为原生 `NSControl`，事件经 action 回调写回 aUI
`Binding`/`State`。该后端按需加载——PyObjC 缺失时 `available()` 返回 `False`，
运行器自动降级到 curses/ASCII。

curses 后端要点：

- 复用现有 `aui.core` 的布局引擎与状态管理，**不修改 core 契约**。
- 后端内部做独立布局遍历（`_walk`），记录每个组件的最终 frame（位置+尺寸），
  绘制到字符网格（`TerminalGrid`），再刷新到 curses 屏幕。
- **全局滚动**：内容高于视口时，整页上下滚动（`PageUp`/`PageDown`），聚焦
  元素始终保持在视口内。
- **键盘焦点导航**：每个交互组件可聚焦（`Tab`/`↑`/`↓`），`Enter` 激活，
  `←`/`→` 调整滑块/下拉/步进器/日期，打字编辑输入框。
- **SwiftUI 控件状态**：组件渲染 focused/disabled 状态；Button 支持
  destructive/cancel 语义角色和 tint/buttonStyle/controlSize；禁用态不可操作。
- **多行 Text**：字符网格上的单词换行（CJK 双宽）。
- 提供 `render_to_string()` 无头渲染方法，便于测试与预览。

AppKit 后端要点：

- 复用同一布局引擎（`size_that_fits` / `place` 计算组件 frame），单位从字符格
  换成逻辑点；`_build` 把每个组件映射为原生控件并放入 `NSWindow.contentView`。
- 原生控件事件（NSControl action）直接写回 aUI `Binding`/`State`，双向绑定。
- 示例 `examples/showcase_appkit.py` 与 curses 共用同一棵 `make_view()` 树
  （`examples/showcase_view.py`），保证两后端展示一致。
- 依赖：`pyobjc-framework-Cocoa`（macOS 图形会话）。

## 后果

- 优点：curses 零依赖、无显示服务器要求、任何终端可用；AppKit 提供真正的
  macOS 原生窗口（非 Tk）；核心布局/状态完全复用，可无终端单元测试；
  无任何 Tk 依赖。
- 代价：curses 终端 UI 无鼠标拖拽、无原生控件外观；AppKit 需要图形会话 +
  PyObjC 安装。
- 演进：curses 后端可扩展鼠标支持（`curses.mousemask`）、更多颜色；
  AppKit 后端可扩展富文本、原生菜单与更多控件映射。

## 参考

- [ADR-0001 架构与设计原则](0001-architecture.md)：后端可插拔设计。
- [ADR-0003 状态驱动渲染策略](0003-render-strategy.md)：整树重建。
