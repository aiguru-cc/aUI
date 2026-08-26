# ADR-0002: 包结构与模块划分

- 状态：已接受
- 日期：2026-08-26

## 背景

需要确定 Python 包布局，支撑"复刻 SwiftUI 语法"且易于扩展。

## 决策

采用 `src/` 布局：

```
src/aui/
├── __init__.py      # 公开 API 再导出（SwiftUI 风格）
├── core/
│   ├── geometry.py  # Size/Point/EdgeInsets/Color/Font
│   ├── view.py      # View 协议、ViewModifier、frame 包装
│   ├── state.py     # State/Binding/ObservableObject/@observable/Environment
│   ├── layout.py    # VStack/HStack/ZStack/Spacer
│   ├── components.py# Text/Button/TextField/Toggle/Slider/Picker/...
│   └── modifiers.py # padding/background/font/... 修饰符
└── backends/
    ├── ascii.py     # 无头 ASCII 渲染
    └── tk.py        # Tkinter 渲染
```

- `core` 保持无 GUI 依赖，可独立测试。
- `backends` 依赖 `core`，负责把视图树渲染为真实控件。
- 顶层 `__init__.py` 统一再导出，用户 `from aui import *` 即可获得 SwiftUI 风格 API。

## 后果

- 优点：关注点分离清晰；新增后端不影响 core；测试无需显示环境。
- 代价：模块较多，学习曲线略高；顶层命名空间需要维护 `__all__`。
