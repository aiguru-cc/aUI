# ADR-0010: 可访问性（Accessibility）支持

- 状态：已接受
- 日期：2026-08-26

## 背景

README 与 BASELINE T25 要求提供可访问性支持（accessibility）。目标：
让 aUI 界面可被屏幕阅读器等辅助技术（assistive technology）描述与操作，
并让无头后端（ASCII/curses）能生成语义化的文本描述。

## 决策

### 1. 声明式可访问性修饰符（值对象，布局透明）

新增 `src/aui/core/accessibility.py`，提供与 SwiftUI 一致的修饰符：

- `accessibilityLabel(label)` — 元素的短名称
- `accessibilityHint(hint)` — 执行操作的结果描述
- `accessibilityValue(value)` — 元素的当前值
- `accessibilityHidden(hidden=True)` — 从可访问性树排除（含子元素）
- `accessibilityElement(children=...)` — 子元素策略：`contain`（默认，
  子元素保持独立）/ `combine`（合并为单元素）/ `ignore`（忽略子元素）

这些修饰符与其它修饰符一样是值对象，不改变布局语义
（`size_that_fits` / `place` 直通）。

### 2. 可访问性树（纯数据结构）

`describe_accessibility(view) -> AccessibilityInfo` 递归遍历视图树，为每个
节点赋予语义角色（`role`：button / text / textfield / toggle / slider /
picker / image / list / ...）、默认标签、当前值，并折叠可访问性修饰符。
`AccessibilityInfo` 是纯数据（role/label/hint/value/hidden/children），
任何后端都可消费。`summary()` 生成人类可读的缩进文本。

### 3. 后端集成

- **curses**：交互式渲染，焦点/激活状态通过颜色与反显呈现；
  `describe_accessibility()` 返回当前视图的可访问性树。
- **ASCII**：提供 `describe_accessibility()`，用于无头检查与文档。

### 4. 组件语义

内置组件自动获得语义角色与默认标签/值（如 Toggle 的 `on/off`、Slider 的
数值、TextField 的 placeholder 作为标签、ProgressView 的百分比）。
显式修饰符可覆盖默认值。

## 后果

- 优点：与 SwiftUI 语义一致；纯数据结构便于测试与多后端消费；无头环境
  可检查可访问性树。
- 代价：Tk 的 `-accessible` 属性依赖平台/Tk 构建支持，不支持时静默降级；
  未提供 Tk 原生焦点环与键盘导航的深度集成（依赖平台）。
- 演进：可增加可访问性动作（`accessibilityAction`）、焦点管理、
  实时区域（live region）。

## 备选方案

- **仅 Tk 原生属性**：无法覆盖 ASCII/curses 与测试，已拒绝。
- **依赖第三方 a11y 库**：违反零依赖定位，已拒绝。
