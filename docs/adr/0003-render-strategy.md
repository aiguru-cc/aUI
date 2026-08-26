# ADR-0003: 状态驱动渲染策略

- 状态：已接受
- 日期：2026-08-26

## 背景

SwiftUI 的核心是"状态变化 → 视图自动更新"。aUI 需要确定渲染更新策略。

## 决策

采用**整树重建（full re-render）**策略：

1. 状态对象（`State` / `ObservableObject`）维护监听者集合。
2. 值变更时调用监听者（视图拥有者的 `_invalidate`）。
3. 后端收到失效信号后，重新求值视图树并重建控件。

`State` 通过 `owner._invalidate()` 通知；`Binding` 写穿到状态源；
`ObservableObject` 通过 `add_listener` 注册刷新回调。

## 后果

- 优点：实现简单、语义清晰、与 SwiftUI 声明式模型一致；状态驱动开箱即用。
- 代价：每次刷新重建全部控件，控件数量大时性能下降；Tk 控件重建有短暂闪烁。
- 演进方向：引入视图身份（identity）+ diff 复用控件（类似 SwiftUI 的 diffing）。
- 已落地：文本测量从近似（0.55×size×len）升级为多行布局（物理换行 + proposal 宽度单词换行 + CJK 双宽字符 + line_limit/line_spacing），见 T18。

## 备选方案

- **增量更新（diff）**：性能更好但复杂度显著上升，作为 v0.2 演进项，本期拒绝。
