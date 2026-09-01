# 使用指南

## 安装

```bash
# 开发模式安装（含 pytest）
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## 快速开始

### 无头渲染（ASCII 后端，无需显示环境）

```python
from aui import Text, Button, VStack, State
from aui.backends.ascii import AsciiBackend

state = State(0)
view = VStack([
    Text(f"Count: {state.wrapped_value}"),
    Button("Increment", action=lambda: state._set(state.wrapped_value + 1)),
], spacing=2)

print(AsciiBackend(width=40, height=10).render(view))
```

运行示例：

```bash
.venv/bin/python examples/counter_ascii.py
```

### 原生窗口（curses 后端 · 推荐默认）

```python
from aui import Text, Button, VStack, State
from aui.backends.curses import CursesBackend

state = State(0)

def make_view():
    return VStack([
        Text(f"Count: {state.wrapped_value}"),
        Button("Increment", action=lambda: state._set(state.wrapped_value + 1)),
    ], spacing=1)

CursesBackend(make_view).run()
```

运行示例：

```bash
.venv/bin/python examples/counter_curses.py
```

操作：`Tab/↑/↓` 切换焦点，打字编辑，`Enter` 激活，`q` 退出。
curses 后端零依赖、无需显示服务器，任何终端均可运行。

无头预览（无需终端）：

```python
from aui.backends.curses import CursesBackend
print(CursesBackend(make_view).render_to_string(80, 15))
```

> aUI 不再使用 Tkinter。原生交互窗口由标准库 curses 提供；如需无头
> 文本渲染用 `AsciiBackend`。

## 状态管理

### State（视图局部状态）

```python
from aui import State

count = State(0)
count.wrapped_value += 1        # 触发失效
count.binding()                 # 生成双向绑定
```

### Binding（双向绑定）

```python
from aui import TextField

field = TextField(count.binding())  # 输入框直接读写 count
```

### ObservableObject（共享状态）

```python
from aui import ObservableObject

class Counter(ObservableObject):
    def __init__(self):
        super().__init__()
        self.count = 0
    def increment(self):
        self.count += 1
        self.object_will_change()
```

### @observable 装饰器

```python
from aui import observable

@observable
class Counter:
    count = 0
```

## 布局

- `VStack(children, spacing, alignment)`：垂直排列
- `HStack(children, spacing, alignment)`：水平排列
- `ZStack(children, alignment)`：层叠
- `Spacer(min_length)`：弹性占位

对齐值：`leading` / `top` / `center` / `trailing` / `bottom` 及组合。

## 运行测试

```bash
.venv/bin/python -m pytest
```

## 自定义组件与渲染后端

- 自定义组件：继承 `View` 实现 `size_that_fits` / `place`（见 `docs/components.md`）。
- 自定义后端：实现 `render(view)`，把 aUI 视图树转成目标控件
  （参考 `src/aui/backends/ascii.py`、`curses.py`、`standard.py`）。

## 已知限制

- curses 后端为整树重绘渲染（终端画布），交互组件量大时性能受终端限制；
  `List` 已使用可视窗口虚拟化。
- 文本测量遵循统一逻辑点/字符网格契约；CJK 按全角双宽处理。
- 动画在 StandardBackend 上由帧驱动，ASCII/curses 以确定性即时状态呈现。
- 主题通过 `StandardTheme` / `AppKitTheme` 配置，`font_scale` 与
  `dynamic_type_size` 提供跨后端动态字体缩放；AppKit 需要可选的 PyObjC，
  StandardBackend 需要带 tkinter 的 Python 发行版。Qt 等额外后端不在内置范围。
