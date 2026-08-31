# ADR-0008: List 懒加载与滚动（T21）

- 状态：已接受
- 日期：2026-08-26

## 背景

`List` 当前把所有行一次性渲染（Tk 后端为每行建控件、curses 为每行占一个
屏幕行）。问题：

1. **大数据量性能差**：数千行时 Tk 控件数、curses 布局遍历均线性增长；
2. **无滚动**：超出容器高度的行无法访问；
3. 与 SwiftUI `List` 的懒加载（lazy）语义不一致。

## 决策

### 1. 虚拟化窗口（core 层，纯逻辑）

`List` 增加**可见窗口（viewport）**概念：

- `List` 持有 `scroll_offset`（首行索引，可绑定 `State`）；
- 布局/渲染时只处理窗口 `[scroll_offset, scroll_offset + visible_count)` 内的行；
- `visible_count` 由容器高度与行高推导（`size_that_fits` 时计算）。

core 不感知后端，只提供窗口计算：`List.visible_rows(viewport_height)` 返回
当前应渲染的行子集。后端调用它决定渲染哪些行。

### 2. Tk 后端：Canvas 滚动容器

`List` 渲染进一个带垂直滚动条的 `ttk.Frame`：

- 内容放入 `Canvas`，滚动条 `command=canvas.yview`，canvas `yscrollcommand` 联动；
- 懒加载：只创建可见窗口内的行控件；滚动时（`<MouseWheel>` / 滚动条拖动）
  更新 `scroll_offset` 并触发重绘（复用 diff 渲染）；
- 行高固定（`row_height`），窗口行数 = `viewport_height // row_height`。

### 3. curses 后端：键盘滚动

- `List` 记录滚动偏移，`j/k` 或 `PageUp/PageDown` 滚动；
- 只布局窗口内的行到屏幕，窗口外行跳过（懒加载）。

### 4. 兼容性

- 不修改既有 `List(rows)` 构造签名；
- 新增可选参数 `scroll_offset`（绑定）、`row_height`（默认按内容测量）；
- 未提供滚动绑定时，内部维护滚动状态（Tk/curses 各自持有）。

## 后果

- 优点：大数据量下只渲染可见行，性能显著提升；与 SwiftUI lazy 语义一致；
  后端各自实现滚动交互。
- 代价：固定行高假设（可变行高需额外测量，作为演进项）；滚动状态与视图
  树的同步需要后端与 core 协作。
- 演进：`ForEach` 显式身份（ADR-0005 演进项）可与懒加载结合，实现列表
  插入/删除的精确复用。
