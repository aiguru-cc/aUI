# ADR-0006: 动画与过渡（T19）

- 状态：已接受
- 日期：2026-08-26

## 背景

SwiftUI 的 `withAnimation` + `.animation(_:)` 修饰符让状态变化以动画方式呈现。
aUI 需要为 Tk 后端提供动画能力，同时保持 core 无 GUI 依赖、可测试。

## 决策

### 1. 动画值类型 `Animation`

`core/animation.py` 定义 `Animation`（值对象）：

- `Animation.ease_in_out(duration)` / `Animation.linear(duration)` / `Animation.spring(...)`
- 提供 `interpolate(start, end, t, curve)` 工具，支持：
  - `float` / `int`：线性插值
  - `Color`：RGB 插值
  - `Size` / `Point`：逐分量插值

### 2. `.animation(_:)` 修饰符

`AnimationModifier` 标记视图在状态变化时应动画化。渲染后端在 diff 时
检测该视图的"旧属性 → 新属性"，用 `after()` 驱动插值帧（Tk 后端）。

### 3. 状态包装 `with_animation`

```python
with_animation(Animation.ease_in_out(0.3)):   # 上下文管理器
    state.wrapped_value = new_value
```

或函数式 `animate(animation, fn)`。被包装的状态变更会携带动画上下文，
后端据此对标记了 `.animation()` 的视图做插值。

### 4. Tk 后端动画实现

- diff 时若视图带 `.animation()` 且属性变化（text 数值、opacity、frame 尺寸/颜色），
  记录 `(widget, attr, start, end, animation)`。
- 用 `root.after(16ms)` 驱动插值帧，每帧 `widget.config(attr=interpolate(...))`。
- 动画结束清理计时器。

### 5. 范围与限制

- 仅 Tk 后端支持动画；ASCII/curses 后端忽略 `.animation()`（无动画语义）。
- 动画属性限于：`opacity`（Tk 用 `state` 模拟或颜色混合）、
  `frame` 尺寸/位置（Tk 用 `place` 几何管理）、颜色过渡。
- 文本内容变化不做逐字动画（成本高、收益低），仅数值类文本可做数字滚动。

## 后果

- 优点：core 保持无 GUI；动画声明式、与 SwiftUI 一致；可单测插值。
- 代价：Tk 动画为帧驱动，性能取决于帧率；部分属性（opacity）在 Tk 上
  需用颜色混合近似。
- 演进：可扩展更多曲线、更多动画属性、`transition`（插入/移除过渡）。

## 备选方案

- **后端专用动画 API**：侵入后端、不可测试，已拒绝。
- **CSS 式 transition 字符串**：不符合 SwiftUI 语法，已拒绝。
