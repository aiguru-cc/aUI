# 组件参考

aUI 组件均为声明式描述对象，由渲染后端（Tkinter/ASCII）转成真实控件。
所有组件可通过 `from aui import *` 导入。

## 文本与按钮

### Text

```python
from aui import Text, Font, Color

Text("Hello")                       # 默认 body 字体
Text("Title").font(Font.title())    # 通过修饰符设置字体
Text("Red").foregroundColor(Color.red)
```

### Button

```python
from aui import Button

Button("Click", action=lambda: print("clicked"))
Button("Delete", action=on_delete, role="destructive")
```

## 输入控件

### TextField（绑定文本）

```python
from aui import TextField, State

name = State("")
TextField(name.binding(), placeholder="输入姓名")
```

### Toggle（开关）

```python
from aui import Toggle, State

enabled = State(False)
Toggle("启用", is_on=enabled.binding())
```

### Slider（滑块）

```python
from aui import Slider, State

volume = State(0.5)
Slider(value=volume.binding(), in_range=(0.0, 1.0), step=0.1)
```

### Picker（下拉选择）

```python
from aui import Picker, State

choice = State("A")
Picker("选项", selection=choice.binding(), options=["A", "B", "C"])
```

## 布局容器

### VStack / HStack / ZStack

```python
from aui import VStack, HStack, ZStack, Spacer, Text

VStack([Text("上"), Text("下")], spacing=8, alignment="leading")
HStack([Text("左"), Spacer(), Text("右")], spacing=4)
ZStack([Text("底层"), Text("顶层")], alignment="center")
```

### Spacer

在 stack 主轴方向吸收剩余空间，实现弹性布局。

## 其他

### Divider

```python
from aui import Divider
Divider()
```

### Image

```python
from aui import Image, Color
Image(system_name="star", color=Color.yellow, size=24)
```

### List

```python
from aui import List, Text
List([Text("行1"), Text("行2")])
```

### Group

不引入布局的分组容器，便于批量应用修饰符。

## 修饰符（Modifiers）

| 修饰符 | 说明 |
|---|---|
| `padding(insets, length)` | 内边距 |
| `background(color)` | 背景色 |
| `foregroundColor(color)` | 前景色 |
| `font(font)` | 字体 |
| `border(color, width)` | 边框 |
| `cornerRadius(radius)` | 圆角 |
| `opacity(value)` | 透明度 0~1 |
| `hidden()` | 隐藏（尺寸归零） |
| `frame(width, height, alignment)` | 固定尺寸 |
| `onTapGesture(action)` | 点击手势 |

修饰符可链式组合：

```python
from aui import Text, Color, padding, background, corner_radius

Text("提示").padding(length=8).background(Color.blue).cornerRadius(6)
```

## 自定义组件

继承 `View` 并实现 `size_that_fits` / `place`（或用容器组合）：

```python
from aui import View, Text, VStack, Size

class Greeting(View):
    def __init__(self, name):
        self._children = [VStack([Text("Hello"), Text(name)])]
    def size_that_fits(self, proposal):
        return self._children[0].size_that_fits(proposal)
    def place(self, origin, size):
        self._children[0].place(origin, size)
```
