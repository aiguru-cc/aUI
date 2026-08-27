# aUI 架构

aUI 是一个基于 Python 的声明式 UI 库，复刻 SwiftUI 的语法与功能。

## 设计目标

- **声明式**：用视图树描述 UI，而非命令式操作控件。
- **状态驱动**：状态变化自动触发视图刷新。
- **零依赖**：后端均为 Python 标准库（Tkinter / curses），无第三方依赖。
- **可测试**：布局与状态逻辑可在无显示环境运行。
- **可访问**：界面可被辅助技术描述与操作（ADR-0010）。

## 分层

```
┌─────────────────────────────────────────────┐
│ 用户代码（View 子类 + State/Binding）         │
├─────────────────────────────────────────────┤
│ aui.core（无 GUI 依赖）                      │
│  ├─ accessibility: label/hint/value/hidden/element + 可访问性树（T25）
│  ├─ animation: Animation/with_animation/animate（T19）
│  ├─ geometry: Size/Point/EdgeInsets/Color/Font
│  ├─ view:     View 协议 / ViewModifier / frame
│  ├─ state:    State/Binding/ObservableObject/@observable/Environment
│  ├─ layout:   VStack/HStack/ZStack/Spacer
│  ├─ components: Text/Button/TextField/Toggle/Slider/Picker/...
│  └─ modifiers: padding/background/font/border/cornerRadius/...
├─────────────────────────────────────────────┤
│ aui.backends（渲染后端，依赖 core）           │
│  ├─ ascii: 无头 ASCII 渲染（测试/文档）       │
│  ├─ tk:    Tkinter 原生控件渲染               │
│  └─ curses: 终端交互 UI（零依赖，推荐默认）    │
└─────────────────────────────────────────────┘
```

## 核心机制

### 1. 视图协议（proposal/response）

每个 `View` 实现 `size_that_fits(proposal) -> Size` 和 `place(origin, size)`。
父视图向子视图提出尺寸建议，子视图返回所需尺寸；布局阶段父视图分配位置。
这与 SwiftUI 的 layout protocol 一致。

### 2. 修饰符链

修饰符是值对象，按应用顺序组合（`padding(...)` 等函数返回新视图）。
渲染后端解释修饰符。`frame` 因改变布局语义，结构性包装内容（`_Frame`）。

### 3. 状态驱动

- `State`：视图局部状态，变更调用 `owner._invalidate()`。
- `Binding`：双向引用，写穿到状态源。
- `ObservableObject` / `@observable`：共享状态，监听者收到变更通知。
- `Environment`：只读依赖注入，沿视图树向下传递。

### 4. 渲染策略

**增量渲染（diff）**：每个视图树节点有结构性身份（路径，如 `root/0/1`）。
状态变更重建视图树后，后端复用路径相同、类型兼容的控件，仅更新变化属性；
类型不兼容或已移除的路径则重建/销毁。避免闪烁并保持输入焦点与滚动位置。
详见 [ADR-0003](adr/0003-render-strategy.md) 与
[ADR-0005](adr/0005-incremental-rendering.md)。

### 5. 可访问性

声明式可访问性修饰符（`accessibilityLabel` / `accessibilityHint` /
`accessibilityValue` / `accessibilityHidden` / `accessibilityElement`）以值
对象附加到视图。`describe_accessibility(view)` 构建纯数据的可访问性树
（语义角色 / 标签 / 提示 / 当前值），后端将其映射到平台辅助技术：
Tk 附加原生 `-accessible` 属性；ASCII/curses 提供无头检查。
详见 [ADR-0010](adr/0010-accessibility.md)。

### 6. 后端选型

- **curses**（推荐默认）：零依赖、无显示服务器、终端交互。
- **Tkinter**：原生窗口控件，需 Python 编译 Tk 支持。
- **ASCII**：无头渲染，用于测试与文档。
详见 [ADR-0004](adr/0004-curses-backend.md)。

## 目录结构

```
src/aui/
├── __init__.py      # 公开 API 再导出
├── core/            # 无 GUI 核心（accessibility/geometry/view/state/layout/components/modifiers/animation/gestures）
└── backends/        # ascii.py / tk.py / curses.py
docs/
├── adr/             # 架构决策记录
├── architecture.md  # 本文档
├── components.md    # 组件参考
└── guide.md         # 使用指南
```

## 相关决策

- [ADR-0001 架构与设计原则](adr/0001-architecture.md)
- [ADR-0002 包结构与模块划分](adr/0002-package-structure.md)
- [ADR-0003 状态驱动渲染策略](adr/0003-render-strategy.md)
- [ADR-0004 后端选型 — curses 终端后端](adr/0004-curses-backend.md)
- [ADR-0005 视图身份与增量渲染（T17）](adr/0005-incremental-rendering.md)
- [ADR-0006 动画与过渡](adr/0006-animation.md)
- [ADR-0007 手势系统](adr/0007-gestures.md)
- [ADR-0008 List 懒加载与滚动](adr/0008-list-virtualization.md)
- [ADR-0010 可访问性支持](adr/0010-accessibility.md)
