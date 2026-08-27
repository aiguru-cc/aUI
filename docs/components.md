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
Text("第一行\n第二行")               # 物理换行
Text("很长的文本会按宽度自动换行", line_limit=3, line_spacing=2)  # 截断 + 行间距
```

> 文本测量支持多行布局：`\n` 物理分行、按 proposal 宽度单词换行、
> CJK 全角字符按双宽测量、`line_limit` 截断、`line_spacing` 行间距。

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

### DatePicker（日期选择）

```python
from datetime import datetime
from aui import DatePicker, State

date = State(datetime(2026, 8, 26))
DatePicker("截止日期", selection=date.binding(), displayed_components="date")
DatePicker("时间", selection=date.binding(), displayed_components="hourAndMinute")
```

`displayed_components`：`"date"`（年月日）、`"hourAndMinute"`（时分）、
`"date hourAndMinute"`（两者）。`in_range` 可限制可选范围。

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

### Stepper（步进器）

```python
from aui import Stepper, State

qty = State(3.0)
Stepper("数量", value=qty.binding(), in_range=(0.0, 10.0), step=1.0)
# 或使用回调
Stepper("数量", on_increment=on_inc, on_decrement=on_dec)
```

### ProgressView（进度条）

```python
from aui import ProgressView

ProgressView(value=0.5, label="加载中")   # 确定进度
ProgressView()                            # 不确定进度（动画）
```

### Form（表单容器）

```python
from aui import Form, TextField, Toggle, Button

Form([
    TextField(name.binding(), placeholder="姓名"),
    Toggle("启用"),
    Button("保存", action=save),
])
```

### NavigationStack（导航容器）

```python
from aui import NavigationStack, Text

NavigationStack("设置", Text("内容"))
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

## 动画（T19）

```python
from aui import Animation, Text, animation, with_animation

# 1. 标记要动画化的视图
view = animation(Text("Hello", color=Color.blue), Animation.ease_in_out(0.4))

# 2. 在动画作用域内修改状态
with with_animation(Animation.ease_in_out(0.4)):
    state.wrapped_value = new_value
```

- `Animation.linear(d)` / `ease_in(d)` / `ease_out(d)` / `ease_in_out(d)` / `spring(d, damping)`
- `with_animation(anim)`：上下文管理器，包裹状态变更
- `animate(anim, fn)`：函数式等价
- 仅 Tk 后端支持帧驱动动画（颜色过渡）；ASCII/curses 忽略 `.animation()`
- 详见 [ADR-0006](adr/0006-animation.md)

## 手势（Gestures）

声明式手势修饰符，由渲染后端检测原生事件并触发回调。手势不影响布局。

| 手势 | 修饰符 | 回调签名 | 触发方式 |
|---|---|---|---|
| 点击 | `on_tap_gesture(view, action)` | `() -> None` | 单击 |
| 长按 | `on_long_press_gesture(view, action, minimum_duration=0.5)` | `() -> None` | 按住超过时长 |
| 拖拽 | `on_drag_gesture(view, action, minimum_distance=10.0)` | `(start, current) -> None` | 拖动超过最小距离 |

```python
from aui import Text, on_tap_gesture, on_long_press_gesture, on_drag_gesture, Color, padding, background

# 点击
on_tap_gesture(padding(Text("Tap")).background(Color.blue), on_tap)

# 长按（按住 0.6s 触发）
on_long_press_gesture(Text("Hold"), on_hold, minimum_duration=0.6)

# 拖拽（回调收到起点与当前点）
def moved(start, current):
    print(f"dx={current.x - start.x}")

on_drag_gesture(Text("Drag"), moved)
```

- Tk 后端：绑定原生 `<Button-1>` / `<B1-Motion>` 事件
- curses 后端：`t` 键循环选中 tappable 区域，Enter 激活
- 详见 [ADR-0007](adr/0007-gestures.md)

## 可访问性（T25）

声明式可访问性修饰符，让界面可被屏幕阅读器等辅助技术描述与操作。
修饰符不影响布局，可链式组合。

| 修饰符 | 说明 |
|---|---|
| `accessibility_label(view, label)` | 元素的短名称 |
| `accessibility_hint(view, hint)` | 执行操作的结果描述 |
| `accessibility_value(view, value)` | 元素的当前值 |
| `accessibility_hidden(view, hidden=True)` | 从可访问性树排除（含子元素） |
| `accessibility_element(view, children=...)` | 子元素策略：`contain` / `combine` / `ignore` |

```python
from aui import (
    Button, Text, VStack,
    accessibility_label, accessibility_hint, accessibility_value,
    accessibility_hidden, accessibility_element, CHILDREN_COMBINE,
)

# 为按钮提供屏幕阅读器标签
accessibility_label(Button("X", action=close), "关闭窗口")

# 提供提示与当前值
accessibility_hint(Button("保存", action=save), "保存你的更改")
accessibility_value(Text("50%"), "百分之五十")

# 隐藏装饰性元素
accessibility_hidden(Text("装饰"), True)

# 将子元素合并为单个可访问性元素
accessibility_element(HStack([Text("姓名"), Text("张三")]), CHILDREN_COMBINE)
```

内置组件自动获得语义角色与默认值：

- `Toggle` → 值 `on` / `off`
- `Slider` → 当前数值
- `TextField` → placeholder 作为标签、输入值作为值
- `ProgressView` → 百分比 / `indeterminate`
- `Button` / `Text` / `Picker` / `Stepper` / `DatePicker` → 标题作为标签

### 可访问性树

```python
from aui import describe_accessibility

info = describe_accessibility(view)   # 纯数据结构（role/label/hint/value/children）
print(info.summary())                 # 缩进的人类可读描述
```

- `TkBackend.describe_accessibility()`：返回当前渲染视图的可访问性树，
  控件创建时自动附加 Tk 原生 `-accessible` 属性
- `AsciiBackend.describe_accessibility(view)` / `CursesBackend.describe_accessibility()`：
  无头检查
- 详见 [ADR-0010](adr/0010-accessibility.md)

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
