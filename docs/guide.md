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

### 原生窗口（Tkinter 后端）

```python
from aui import Text, Button, VStack, State
from aui.backends.tk import TkBackend

state = State(0)

def make_view():
    return VStack([
        Text(f"Count: {state.wrapped_value}"),
        Button("Increment", action=lambda: state._set(state.wrapped_value + 1)),
    ], spacing=8)

backend = TkBackend()
backend.render(make_view())
backend.mainloop()
```

运行示例：

```bash
.venv/bin/python examples/counter_tk.py
```

> Tkinter 后端需要图形显示环境（macOS 桌面 / X11 / Windows），且 Python
> 需编译 Tk 支持（Homebrew 的 `python-tk`）。若 `import tkinter` 报
> `No module named '_tkinter'`，请改用 curses 后端。

### 终端交互（curses 后端，推荐默认）

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

操作：`Tab/↑/↓` 切换输入框焦点，打字编辑，`Enter` 确认，`q` 退出。
curses 后端零依赖、无需显示服务器，任何终端均可运行。

无头预览（无需终端）：

```python
from aui.backends.curses import CursesBackend
print(CursesBackend(make_view).render_to_string(80, 15))
```

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
  （参考 `src/aui/backends/ascii.py` 与 `tk.py`）。

## 已知限制

- Tkinter 后端为整树重建渲染，控件量大时性能下降。
- 文本测量为近似值（按字符数 × 字体系数估算）。
- 尚未支持：动画、手势系统、列表懒加载、精确文本换行。
