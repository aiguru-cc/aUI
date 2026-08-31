# ADR-0007: 手势系统

- 状态：已接受
- 日期：2026-08-26

## 背景

SwiftUI 提供声明式手势修饰符（`onTapGesture`、`onLongPressGesture`、
`onDragGesture` 等）。aUI 已有 `onTapGesture` 修饰符，但**没有任何后端
处理它**——点击手势在 Tk/curses 中均未绑定，属于功能缺口。T20 需要建立
完整的手势系统。

## 决策

### 1. 手势为声明式值对象 + 修饰符

- `LongPressGesture` / `DragGesture` 为不可变值对象（参数：时长/最小距离）。
- `onLongPressGesture` / `onDragGesture` 修饰符把回调附加到视图。
- 手势修饰符**不影响布局**（`size_that_fits` / `place` 透传），与
  `onTapGesture` 语义一致。
- 模块：`src/aui/core/gestures.py`，从 `aui` 顶层导出。

### 2. 后端负责事件检测

- **Tk 后端**：`_draw` 收集每个 path 的手势修饰符，widget 创建后
  `_bind_gestures` 绑定原生事件：
  - tap → `<Button-1>`
  - long-press → `<ButtonPress-1>` 启动定时器 + `<ButtonRelease-1>` 取消
  - drag → `<ButtonPress-1>` + `<B1-Motion>` + `<ButtonRelease-1>`，
    回调收到 `(start, current)` 点坐标，超过 `minimum_distance` 才触发
- **curses 后端**：键盘事件循环，`t` 键循环选中 tappable 区域，Enter 激活
  （tap 回调 / Toggle 翻转）。长按与拖拽在终端以键盘语义近似。

### 3. 回调签名

- tap / long-press：`Callable[[], None]`
- drag：`Callable[[Point, Point], None]`（起点、当前点）

## 后果

- 优点：手势声明式、跨后端一致、布局无关；Tk 原生事件绑定自然。
- 代价：curses 后端长按/拖拽仅近似（无鼠标语义）；drag 回调坐标是
  widget 局部坐标，未做视图坐标换算。
- 演进：可增加 `MagnificationGesture` / `RotationGesture`、拖拽坐标换算、
  curses 鼠标支持（`curses.mousemask`）。

## 备选方案

- **手势作为独立 View 包装器**：与修饰符体系重复，且破坏现有
  `onTapGesture` 一致性，已拒绝。
