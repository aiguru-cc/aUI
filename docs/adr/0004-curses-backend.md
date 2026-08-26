# ADR-0004: 后端选型 — curses 终端后端

- 状态：已接受
- 日期：2026-08-26

## 背景

Tkinter 后端在目标开发机（Homebrew Python 3.14）上不可用——该解释器未编译
`_tkinter` 模块。需要评估"不用 Tk 支持、Python 原生编写"的替代路径。

## 备选方案

1. **curses 终端 UI**：标准库自带，零依赖，跨平台，当前环境直接可用。
2. **自绘 GUI**（ctypes 调系统图形 API）：无官方 Python 绑定，需自实现窗口/
   事件/绘制/文本渲染，数周工作量，平台绑定严重。
3. **Web 后端**（http.server + 浏览器）：外观现代但需 HTML/JS 桥接层，
   引入异步通信复杂度，3–5 天工作量。
4. **修复 Tk**（`brew install python-tk`）：只解决单机问题，仍受 Tk 8.5 限制。

## 决策

新增 **curses 终端后端**（`src/aui/backends/curses.py`）作为 Tkinter 之外的
默认可用后端。

- 复用现有 `aui.core` 的布局引擎与状态管理，**不修改 core 契约**。
- 后端内部做独立布局遍历（`_walk`），记录每个组件的最终 frame（位置+尺寸），
  绘制到字符网格（`TerminalGrid`），再刷新到 curses 屏幕。
- 事件循环：键盘输入 → 焦点在文本域间移动、编辑；Enter 确认；q 退出。
- 提供 `render_to_string()` 无头渲染方法，便于测试与预览。

## 后果

- 优点：零依赖、无显示服务器要求、当前环境即可用；核心代码完全复用；
  布局/绘制可无终端单元测试。
- 代价：终端 UI 无鼠标拖拽、无原生控件外观；文本输入为逐字符编辑；
  组件默认尺寸（Tk 像素单位）需在 curses 后端适配为单行高度。
- 演进：curses 后端可扩展鼠标支持（`curses.mousemask`）、颜色（`start_color`）。

## 参考

- [ADR-0001 架构与设计原则](0001-architecture.md)：后端可插拔设计。
- [ADR-0003 状态驱动渲染策略](0003-render-strategy.md)：整树重建。
