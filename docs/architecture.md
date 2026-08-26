# aUI 架构

aUI 是一个基于 Python 的声明式 UI 库，复刻 SwiftUI 的语法与功能。

## 设计目标

- **声明式**：用视图树描述 UI，而非命令式操作控件。
- **状态驱动**：状态变化自动触发视图刷新。
- **零依赖**：后端均为 Python 标准库（Tkinter / curses），无第三方依赖。
- **可测试**：布局与状态逻辑可在无显示环境运行。

## 分层

```
┌─────────────────────────────────────────────┐
│ 用户代码（View 子类 + State/Binding）         │
├─────────────────────────────────────────────┤
│ aui.core（无 GUI 依赖）                      │
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

整树重建（full re-render）：状态变更 → 后端重建视图树 → 重建控件。
详见 [ADR-0003](adr/0003-render-strategy.md)。

### 5. 后端选型

- **curses**（推荐默认）：零依赖、无显示服务器、终端交互。
- **Tkinter**：原生窗口控件，需 Python 编译 Tk 支持。
- **ASCII**：无头渲染，用于测试与文档。
详见 [ADR-0004](adr/0004-curses-backend.md)。

## 目录结构

```
src/aui/
├── __init__.py      # 公开 API 再导出
├── core/            # 无 GUI 核心（geometry/view/state/layout/components/modifiers）
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
