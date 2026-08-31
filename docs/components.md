# 组件参考

aUI 组件均为声明式描述对象，由渲染后端（curses 终端 / ASCII 无头）转成控件。
所有组件可通过 `from aui import *` 导入。

## 文本与按钮

### Text

```python
from aui import Text, Font, Color

Text("Hello")                       # 默认 body 字体
Text("Title").font(Font.title())    # 链式修饰符
Text("Red").foregroundColor(Color.red)
Text("第一行\n第二行")               # 物理换行
Text("很长的文本会按宽度自动换行", line_limit=3, line_spacing=2)  # 截断 + 行间距
```

> 文本测量支持多行布局：`\n` 物理分行、按 proposal 宽度单词换行、
> CJK 全角字符按双宽测量、`line_limit` 截断、`line_spacing` 行间距。

### Button

```python
from aui import Button, ButtonStyle, Color, ControlSize

Button("Click", action=lambda: print("clicked"))
Button("Delete", action=on_delete, role="destructive")
Button("Cancel", action=cancel, role="cancel")
Button("Save", action=save).disabled()

btn = (Button("发布", action=publish)
       .button_style(ButtonStyle.BORDERED_PROMINENT)
       .control_size(ControlSize.LARGE)
       .tint(Color.green))
```

`role` 只表达 SwiftUI 的 `destructive` / `cancel` 语义；颜色、边框、尺寸、圆角、
阴影和宽度分别使用 `.tint()`、`.button_style()`、`.control_size()`、
`.clip_shape()`、`.shadow()` 和 `.frame()`。所有控件通过统一 `.disabled()` 修饰器
进入禁用态。

控件构造器不接受 `enabled=`；可将 `.disabled(condition)` 放在单个控件或容器上，
禁用状态会按环境向后代传播。

## 输入控件

### TextField（绑定文本）

```python
from aui import TextField, State

name = State("")
TextField(name.binding(), placeholder="输入姓名")
TextField(name.binding(), placeholder="禁用").disabled()   # 链式禁用
```

### searchable 与 TextEditor

```python
from aui import State, Text, TextEditor

query = State("")
notes = State("第一行\n第二行")
Text("内容").searchable(query.binding(), prompt="搜索")
TextEditor(notes.binding(), placeholder="输入备注", min_height=96)
```

macOS 后端分别使用原生搜索框和可换行编辑控件；两个组件都通过 `Binding`
实时读写状态。

### SecureField（密码输入）

```python
from aui import SecureField, State

pwd = State("")
SecureField(pwd.binding(), placeholder="密码")   # 渲染为 ***，绑定保留真实值
```

### Toggle（开关）

```python
from aui import Toggle, State

enabled = State(False)
Toggle("启用", is_on=enabled.binding())
Toggle("大号开关").control_size(ControlSize.LARGE)
Toggle("禁用").disabled()
```

### Slider（滑块）

```python
from aui import Slider, State

volume = State(0.5)
Slider(value=volume.binding(), in_range=(0.0, 1.0), step=0.1).tint(Color.blue)
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

### ColorPicker（颜色选择）

```python
from aui import ColorPicker, Color, State

color = State(Color.teal)
ColorPicker("主题色", selection=color.binding())
```

### Picker（下拉选择）

```python
from aui import Picker, State

choice = State("A")
Picker("选项", selection=choice.binding(), options=["A", "B", "C"])
```

### Picker 分段样式

```python
from aui import Picker, PickerStyle, State

tab = State("概览")
Picker("", selection=tab.binding(), options=["概览", "详情", "历史"]) \
    .picker_style(PickerStyle.SEGMENTED)
```

### Gauge（指标）与 Link（链接）

```python
from aui import Gauge, Link

Gauge(72, in_range=(0, 100), label="容量")
Link("Python 文档", "https://docs.python.org/3/")
```

`Gauge` 会把指定范围归一化并在 AppKit 中映射为 `NSLevelIndicator`；`Link`
由用户激活后交给 macOS 默认 URL 处理程序打开。

## 窗体与多栏导航

### NavigationSplitView（二栏/三栏）

```python
from aui import NavigationSplitView

layout = NavigationSplitView(
    sidebar=sidebar_view,
    content=list_view,       # 省略 content 即为二栏布局
    detail=detail_view,
)
```

默认在宽屏显示三栏；中等宽度自动折叠中间栏；紧凑宽度只显示详情栏。
`sidebar_width` 和 `content_width` 可用 `(minimum, ideal, maximum)` 调整。

`column_visibility` 接受 `Binding`，支持 automatic、all、doubleColumn 和
detailOnly；`preferred_compact_column` 决定紧凑宽度显示 sidebar、content 或
detail。`.navigation_split_view_style()` 支持 balanced/prominentDetail，
`.navigation_split_view_column_width()` 可分别覆盖三列的最小、理想和最大宽度。

### Inspector 辅助面板

`.inspector(is_presented, content)` 在宽窗口中创建带原生背景和分隔线的 trailing
属性面板；紧凑宽度自动改为覆盖式单面板。`.inspector_column_width()` 调整最小、
理想和最大宽度，`.inspector_background()` 设置面板表面颜色。关闭会回写 Binding。

### Window 与 WindowGroup

```python
from aui import Size, Window, WindowGroup
from aui.backends.appkit import AppKitApplication

scenes = WindowGroup([
    Window("主窗口", make_main_view, default_size=Size(1080, 700)),
    Window("检查器", make_inspector, id="inspector",
           default_size=Size(360, 480)),
])
AppKitApplication(scenes).run()
```

`Window` / `Settings` 支持 `WindowStyle`、`WindowResizability`、`WindowLevel`、
`default_position`、`min_size`、`max_size`、`restoration_id` 和
`WindowRestorationBehavior`。AppKit 会映射标题栏透明度、resize mask、浮动层级、
原生内容尺寸限制、屏幕位置与 frame autosave name。

`Window` 是纯 Python 的声明式窗体描述；`AppKitApplication` 将一个或多个窗体
映射为独立的原生 `NSWindow`。

窗口还可声明跨平台生命周期回调：`on_resize(Size)`、`on_focus_changed(bool)` 与
`on_close()`。AppKit 与 Standard 后端均在原生窗口事件发生时调用它们；回调中更新
`State` 会自动驱动视图重建。

```python
Window(
    "Workspace", make_view,
    on_resize=lambda size: viewport._set(size),
    on_focus_changed=lambda focused: is_active._set(focused),
    on_close=lambda: save_draft(),
)
```

### Settings 与 SettingsLink

```python
from aui import Settings, SettingsLink, Window, WindowGroup
from aui.backends.appkit import AppKitApplication

scenes = WindowGroup([
    Window("Workspace", lambda: VStack([Text("Main"), SettingsLink()])),
    Settings(make_settings_view),
])
AppKitApplication(scenes).run()
```

`Settings` 是懒创建的单实例场景：应用启动时不显示，第一次点击 `SettingsLink`
或按 `⌘,` 时创建，再次触发只会聚焦已有窗口。一个应用最多声明一个 Settings
场景；它可与 `AppStorage`/`JSONStore` 组合保存偏好。

### WindowLink 与按需窗口

```python
from aui import Window, WindowGroup, WindowLink

scenes = WindowGroup([
    Window("Main", lambda: WindowLink("打开检查器", "inspector")),
    Window("Inspector", make_inspector, id="inspector",
           initially_presented=False),
])
```

`WindowLink` 对应 SwiftUI 环境中的 `openWindow(id:)`：第一次触发创建目标窗口，
之后只把同一窗口带到前台。程序化场景可调用 `AppKitApplication.open_window(id)`，
或通过可注入、可测试的 `OpenWindowAction` 转发。未知 ID 返回 `False`。

`DismissWindowLink()` 默认关闭它所在的当前窗口，也可传 `window_id` 关闭指定场景。
对应的 `DismissWindowAction` 可供程序逻辑调用。关闭保留原生后端与视图状态，之后
再次使用 `WindowLink` 会恢复同一窗口实例。

### MenuBarExtra

```python
extra = MenuBarExtra("aUI", [
    Button("显示主窗口", lambda: app.open_window("main")),
    Divider(),
    Button("退出", quit_app).keyboard_shortcut(KeyboardShortcut("q")),
], system_name="sparkles")

AppKitApplication(WindowGroup([main_window, extra])).run()
```

`MenuBarExtra` 映射为原生 `NSStatusItem`，可显示文字或 SF Symbol。菜单支持动作、
禁用状态、`Divider` 和键盘快捷键；状态项由应用强引用管理，不会被系统提前
回收。同一个 `Divider` 也可用于普通 `Menu`。

### Commands 与 CommandMenu

```python
commands = Commands([
    CommandMenu("File", [
        Button("新建", create).keyboard_shortcut(KeyboardShortcut("n")),
        Divider(),
        Button("关闭", close),
    ]),
])
AppKitApplication(main_window, commands=commands).run()
```

每个 `CommandMenu` 映射为 macOS 主菜单栏中的一级菜单。命令动作执行后，应用会
刷新所有已打开的声明式窗口，使共享 `State` 变化立即显示。菜单 ID 必须唯一；
也可直接把 `CommandMenu` 列表传给 `AppKitApplication(commands=...)`。

### NavigationPath 与 NavigationLink

```python
from aui import NavigationLink, NavigationPath, NavigationStack, Text, VStack

path = NavigationPath()

def make_view():
    root = VStack([
        NavigationLink("打开详情", "article-1", path),
    ])
    return NavigationStack(root.navigation_title("资料库"), path=path).navigation_destination(
        str, lambda article_id: Text(f"详情：{article_id}")
    )
```

`NavigationLink` 把任意可哈希值压入路径；`navigation_destination` 根据值类型
生成目标视图。AppKit 显示原生返回按钮，curses 后端使用 `Esc` 返回。
`NavigationPath` 还支持 `append()`、`remove_last()`、`clear()` 和变化订阅。

目标页面可以独立声明导航栏配置，返回时会自动恢复上一级设置：

```python
detail = (
    Text("详情")
    .navigation_title("文章")
    .navigation_bar_title_display_mode("large")
    .navigation_bar_background(Color(0.94, 0.96, 1.0))
)
```

`.navigation_bar_hidden()` 隐藏当前目的地的导航栏并回收布局空间。AppKit 使用
原生标题、返回按钮和背景，ASCII/curses 后端保持相同的可见性语义。

### Sheet 与 Alert

```python
from aui import Button, Size, State, Text

show_sheet = State(False)
show_alert = State(False)

view = Button("编辑", lambda: show_sheet._set(True)).sheet(
    show_sheet.binding(),
    lambda dismiss: Button("完成", dismiss),
    title="编辑器",
    size=Size(560, 380),
).alert(
    "删除项目？",
    show_alert.binding(),
    "此操作无法撤销。",
    [
        Button("删除", delete, role="destructive"),
        Button("取消", lambda: None, role="cancel"),
    ],
)
```

Sheet 内容闭包可以声明一个 `dismiss` 参数，用于关闭原生 sheet。Alert 按钮角色
支持 `cancel` 和 `destructive`，AppKit 会将 destructive alert 映射为
系统关键警告样式。两种呈现都由 `Binding[bool]` 控制。

Sheet 支持 `.presentation_detents()`（medium、large、固定高度、比例高度）、选择
Binding、`.presentation_drag_indicator()`、`.interactive_dismiss_disabled()`、
`.presentation_background_interaction()` 和 `.presentation_corner_radius()`。
`.full_screen_cover()` 使用父窗口可用尺寸创建覆盖式呈现。

### Popover 与 Confirmation Dialog

```python
help_button = Button("帮助", lambda: show_help._set(True)).popover(
    show_help.binding(),
    lambda dismiss: Button("关闭", dismiss),
    size=Size(320, 220),
    edge="trailing",
)

view = content.confirmation_dialog(
    "选择操作",
    show_actions.binding(),
    buttons=[
        Button("归档", archive),
        Button("删除", delete, role="destructive"),
        Button("取消", lambda: None, role="cancel"),
    ],
)
```

Popover 可选择 `top`、`bottom`、`leading`、`trailing` 锚定边缘，内容闭包同样
可以接收 `dismiss`。用户点击外部区域关闭 transient popover 时，绑定会自动写回
`False`。

### Menu、Toolbar 与快捷键

```python
from aui import KeyboardShortcut, Menu, Button, ToolbarItem

menu = Menu("操作", [
    Button("打开", open_document).keyboard_shortcut(KeyboardShortcut("o")),
    Button("删除", delete, role="destructive"),
])

view = content.toolbar([
    ToolbarItem(
        "add",
        Button("添加", add).keyboard_shortcut(KeyboardShortcut("n")),
        placement="primaryAction",
    ),
])
```

快捷键修饰键支持 `command`、`option`、`control`、`shift`。AppKit 将 Menu
映射为原生 `NSMenuItem`，Toolbar 显示在窗口标题栏；curses 使用方向键选择
Menu 项并按 Enter 激活。

### Table、TableColumn 与 SortOrder

```python
from aui import SortOrder, State, Table, TableColumn

selection = State(None)
sort = State(SortOrder("name", ascending=True))

table = Table(
    rows=people,
    columns=[
        TableColumn("姓名", "name", width=180),
        TableColumn("得分", "score", width=80),
        TableColumn("显示名", "display", value=lambda row: row.full_name),
    ],
    selection=selection.binding(),
    id_key="id",
    sort_order=sort.binding(),
)
```

行可以是对象或字典。默认通过列的 `key` 读取值，也可以提供 `value` 闭包。
AppKit 使用可滚动的原生 `NSTableView`，选择结果写入 `selection`；ASCII/curses
提供表头、单元格和行选择降级。

当 selection Binding 保存 `set`/`frozenset` 时自动启用多选，也可通过
`allows_multiple_selection` 显式设置。sort Binding 可以保存 `SortOrder` 列表，
按顺序执行稳定的多列排序。`TableColumn` 支持可绑定 `visible`、minimum/ideal/
maximum 宽度；空表使用 `empty_message`，并可关闭交替行背景。

## 网格、标签内容与空状态

```python
from aui import ContentUnavailableView, Grid, GridRow, LabeledContent, Text

metadata = Grid([
    GridRow([Text("平台"), Text("macOS")]),
    GridRow([Text("渲染器"), Text("AppKit")]),
])

LabeledContent("版本", "1.0")
ContentUnavailableView("没有结果", "magnifyingglass", "请尝试其它关键词")
```

`Grid` 会统计所有 `GridRow` 的单元格尺寸，因此相同列能跨行对齐。
`ContentUnavailableView` 使用标题、SF Symbol 和说明文字建立标准空状态。

## Shape 与 SF Symbols

```python
from aui import Circle, Color, Image, Rectangle, RoundedRectangle, Size, StrokeStyle, UnevenRoundedRectangle

Circle(size=Size(40, 40)).fill(Color.indigo)
Rectangle(size=Size(80, 32)).stroke(Color.blue, line_width=2)
RoundedRectangle(corner_radius=10, size=Size(100, 44)).fill(Color.teal)
UnevenRoundedRectangle(24, 6, 6, 24, size=Size(120, 64)) \
    .fill(Color.blue).stroke_border(
        Color.white,
        style=StrokeStyle(4, "round", "round", dash=(10, 4)),
    )
Image(system_name="star.fill", color=Color.yellow, size=24)
```

所有 Shape 支持 `.inset()` 和完全绘制在边界内的 `.stroke_border()`；
`UnevenRoundedRectangle` 支持四个独立角半径和 circular/continuous 样式语义。
`.stroke()`/`.stroke_border()` 可接收完整 `StrokeStyle`，包含 line cap、line join、
miter limit、dash pattern 和 dash phase。
`.trim(from_, to)` 使用 0...1 的归一化路径范围，可构建环形进度和分段轨迹；
`FillStyle(eo_fill=True, antialiased=False)` 控制偶奇填充规则与边缘抗锯齿。
AppKit 后端使用 Core Animation 路径真实绘制非对称圆角，并通过系统 Symbol API 加载
`Image(system_name=...)`；`Image.from_file()` 和 `Image.from_data()` 则创建原生
位图。无有效图片时不会显示灰色占位块。

`Image` 支持 `.resizable()`、`.scaled_to_fit()`、`.scaled_to_fill()`、
`.interpolation()` 与 `.antialiased()`。SF Symbol 可组合 `.symbol_variant("circle",
"fill")`，并通过 `SymbolRenderingMode` 使用 monochrome、hierarchical、palette 或
multicolor 原生符号配置；`.image_scale()` 和 `.symbol_weight()` 控制系统图标的
尺寸层级与字重。`.resizable(cap_insets=..., resizing_mode="tile")` 支持九宫格
拉伸或平铺。

`Image(system_name="speaker.wave.3", variable_value=0.65)` 或
`.variable_symbol(0...1)` 创建可变值 SF Symbol；不支持该系统 API 的旧 macOS
自动回退为相同名称的普通符号。

### Gradient、Material、Shadow 与 Overlay

```python
from aui import (
    AngularGradient, Color, EllipticalGradient, LinearGradient, Material, RadialGradient, Size, Text,
)

hero = LinearGradient(
    [Color.indigo, Color.purple, Color.pink],
    start_point=(0, 0),
    end_point=(1, 1),
    size=Size(480, 180),
)
color_wheel = AngularGradient(
    [Color.red, Color.yellow, Color.green, Color.blue, Color.red],
    center=(0.5, 0.5), start_angle=-90, end_angle=270,
)
spotlight = RadialGradient(
    [Color.white, Color.blue], start_radius=12, end_radius=120,
)
oval_glow = EllipticalGradient(
    [Color.yellow, Color.clear],
    start_radius_fraction=0.1, end_radius_fraction=0.65,
)

card = Text("Material card") \
    .padding(length=20) \
    .material_background(Material.REGULAR) \
    .shadow(radius=12, y=4) \
    .overlay(Text("New"), alignment="topTrailing")
```

可用材质包括 `ULTRA_THIN`、`THIN`、`REGULAR`、`THICK`、`ULTRA_THICK`
和 `SIDEBAR`。`AngularGradient` 支持中心点、起止角度和任意色标；
`RadialGradient` 支持 start/end radius，`EllipticalGradient` 使用相对视图边界的
半径比例。所有渐变均可
通过 `.color_at(0...1)` 进行后端无关的颜色采样。AppKit 使用 `CAGradientLayer`、`NSVisualEffectView` 与 CALayer
阴影实现，不生成中间位图。

## 结构型视图

```python
from aui import AnyView, EmptyView, ForEach, GroupBox, Text, ViewThatFits

rows = ForEach(
    items,
    lambda item: Text(item.title),
    id="id",
    spacing=8,
)

group = GroupBox("项目", rows)

adaptive = ViewThatFits([
    WideToolbar(),
    CompactToolbar(),
], axis="horizontal")

conditional = AnyView(Text("已登录") if signed_in else EmptyView())
```

- `ForEach` 使用可哈希且唯一的数据 ID 缓存视图，数据重排后仍保持身份；
- `ViewThatFits` 选择第一个能容纳在提议尺寸中的候选；
- `AnyView` 提供类型擦除但保留布局和可访问性；
- `EmptyView` 不占空间；
- `GroupBox` 提供带标签的语义分组和 AppKit 卡片视觉。

## 延迟 Stack 与 Grid

```python
from aui import GridItem, LazyHGrid, LazyHStack, LazyVGrid, LazyVStack, Text

list_content = LazyVStack(
    items,
    lambda item: Text(item.title),
    id="id",
    spacing=8,
)

grid = LazyVGrid(
    items,
    [GridItem.adaptive(minimum=140, maximum=240)],
    lambda item: ProjectCard(item),
    id="id",
    spacing=12,
    row_spacing=12,
)

horizontal_grid = LazyHGrid(
    items,
    [GridItem.fixed(72), GridItem.flexible(60, 100)],
    lambda item: Text(item.title),
    id="id", spacing=12, column_spacing=16,
)
```

`GridItem` 支持：

- `GridItem.fixed(size, spacing=None, alignment="center")`：固定轨道；
- `GridItem.flexible(minimum, maximum, spacing=None, alignment="center")`：共享剩余空间；
- `GridItem.adaptive(minimum, maximum, spacing=None, alignment="center")`：按可用空间自动增加或减少轨道数。

每个 `GridItem` 可覆盖网格的默认轨道间距。纵向网格支持 leading/center/trailing
列对齐，横向网格支持 top/center/bottom 行对齐。

`LazyVGrid` 按行从左到右填充，`LazyHGrid` 按列从上到下填充。Lazy 容器在
首次布局前不会调用内容构建器，构建后通过数据 ID 复用子视图。

## ScrollViewReader 与程序化滚动

```python
from aui import Button, ScrollViewReader, Text, VStack

def content(proxy):
    return VStack([
        Button("跳到第 50 行", lambda: proxy.scroll_to(50, anchor="center")),
        *[Text(f"Row {index}").id(index) for index in range(100)],
    ])

view = ScrollViewReader(content)
```

`.id(value)` 注册可哈希的稳定视图 ID。`scroll_to` 支持 `top`、`center`、
`bottom` 锚点；AppKit 直接滚动原生 clip view，curses 更新终端滚动偏移。

滚动容器还支持 `.scroll_indicators()`、`.default_scroll_anchor()`、
`.scroll_target_behavior()`、`.scroll_clip_disabled()` 与 `.content_margins()`。
`.scroll_position(binding, anchor=...)` 将稳定视图 ID 作为当前位置；AppKit 在布局
完成后通过原生 clip view 定位，并支持首次显示时居中或停靠底部。

## 键盘快捷键与默认焦点

`.keyboard_shortcut("s")` 默认使用 Command 修饰键，也可传入
`KeyboardShortcut.default_action()` 或 `cancel_action()` 创建 Return/Escape 动作。
AppKit 映射为原生 key equivalent，curses 对无修饰键和默认/取消动作执行相同分发。

`.default_focus(binding, equals=...)` 只在焦点尚未指定时设置初始焦点，不覆盖用户
后续选择；`.focus_section(id)` 标记逻辑焦点区域。`.on_key_press(keys, action)` 接收
`KeyPress`，返回 `KeyPressResult.HANDLED` 可阻止后续默认键盘处理。

## GeometryReader 与 GeometryProxy

```python
from aui import GeometryReader, HStack, Text, VStack

def adaptive(proxy):
    items = [Text("Sidebar"), Text("Content"), Text("Inspector")]
    return HStack(items) if proxy.size.width >= 700 else VStack(items)

view = GeometryReader(adaptive)
```

`GeometryReader` 占满父级提供的有限尺寸；遇到无界轴时使用子视图的自然尺寸。
代理提供 `size`、`safe_area_insets`，以及 `frame("local")` 和
`frame("global")`。返回的 `Rect` 包含 `min_x/min_y/max_x/max_y/mid_x/mid_y`，
三个后端使用同一套几何语义。当前不支持 SwiftUI 的命名坐标空间。

## Layout、AnyLayout 与高级布局修饰符

```python
class DiagonalLayout(Layout):
    def size_that_fits(self, proposal, subviews):
        return Size(320, 180)

    def place_subviews(self, bounds, proposal, subviews):
        return [
            LayoutPlacement(subview, Point(bounds.origin.x + i * 24,
                                           bounds.origin.y + i * 18),
                            subview.size_that_fits(Size(100, 40)))
            for i, subview in enumerate(subviews)
        ]

view = AnyLayout(DiagonalLayout())(children)
```

`LayoutSubview` 提供 `size_that_fits()` 和 `priority`，布局返回共享给 AppKit、
curses 与 ASCII 的 `LayoutPlacement`。内置 `HStackLayout`、`VStackLayout`、
`ZStackLayout` 可放进 `AnyLayout`，用于状态驱动的算法切换。

高级修饰符包括：

- `.layout_priority(value)`：压缩时优先保留高优先级子视图；
- `.fixed_size(horizontal, vertical)`：在指定轴使用自然尺寸；
- `.offset(x, y)`、`.position(x, y)`：调整实际渲染坐标；
- `.z_index(value)`：控制重叠视图绘制顺序；
- `.aspect_ratio(ratio, "fit" | "fill")`：按比例测量；
- `.safe_area_inset(edge, length)`：为指定安全边预留空间；
- `.ignores_safe_area(edges)`：声明忽略安全边。macOS 普通内容区本身已排除标题栏，
  因而该修饰符在 AppKit 窗口内容区通常不产生额外位移。

## OutlineGroup 层级数据

```python
from aui import OutlineGroup, State, Text

expanded = State({"projects"})
outline = OutlineGroup(
    nodes,
    children="children",
    content=lambda node: Text(node.title),
    id="id",
    expanded=expanded.binding(),
)
```

`children` 和 `id` 均可传属性名、字典键名或函数。所有层级的 ID 必须唯一且
可哈希；内容视图按 ID 缓存，展开/折叠后仍保持身份。省略 `expanded` 时组件使用
内部临时状态；传入 `Binding[set]` 后，多个视图可共享和恢复展开位置。

`default_expanded_depth` 可在没有外部 expanded Binding 时初始化展开层级；
`expand_all()` / `collapse_all()` 执行批量操作。selection Binding 支持单个 ID 或
ID set 多选，`visible_nodes` 提供当前可见节点及深度。AppKit 使用原生
`NSOutlineView`，原生 disclosure 与选择变化会反向更新两个 Binding。

## FocusState 与声明式焦点

```python
from aui import FocusState, TextField

focused_field = FocusState("name")

name_field = TextField(name.binding(), "姓名").focused(
    focused_field.binding(), equals="name"
)
email_field = TextField(email.binding(), "邮箱").focused(
    focused_field.binding(), equals="email"
)
```

将 `focused_field` 写为目标 ID 会让 AppKit 把对应原生控件设为 first responder；
用户开始或结束编辑时，焦点状态会反向更新。布尔焦点状态失焦后写为 `False`，
类型化字段 ID 失焦后写为 `None`。curses 的 Tab 和方向键使用相同绑定。

## 生命周期与提交

```python
field = TextField(query.binding(), "搜索") \
    .focused(focus.binding(), equals="query") \
    .on_submit(run_search) \
    .submit_label("search")

content = content.on_appear(load_data).on_disappear(save_draft)
```

`submit_label` 支持 `return`、`done`、`go`、`send`、`search`、`next`、
`continue` 和 `join`。AppKit 将 Return 映射到原生控件 action；curses 使用
Enter。`on_disappear` 在内容重建前及窗口关闭时执行。

## ShareLink 与 PasteButton

```python
from aui import PasteButton, ShareLink, State

text = State("")
paste = PasteButton("从剪贴板粘贴", text=text.binding())
share = ShareLink(
    ["https://example.com", "/path/to/report.pdf"],
    subject="项目报告",
    message="请查看附件",
)
```

AppKit 中 `ShareLink` 打开原生 `NSSharingServicePicker`，字符串 URL、普通文本和
`pathlib.Path` 文件均可共享；`subject` 与 `message` 会一同加入共享内容。
`PasteButton` 读取系统文本剪贴板，可写入 `Binding[str]`、调用 `on_paste`，或
同时执行两者。无头测试可通过 `share_handler` 和 `provider` 注入确定性行为。

## FileImporter 与 FileExporter

```python
content = content.file_importer(
    show_import.binding(), ["json", "txt"], imported, allows_multiple=True
).file_exporter(
    show_export.binding(), lambda: report_text, "report.txt", exported
)
```

两个修饰符由 `Binding[bool]` 控制呈现，在 AppKit 中映射到 `NSOpenPanel` 和
`NSSavePanel`。完成回调接收 `FileDialogResult`，通过 `urls`、`error`、
`cancelled` 和 `is_success` 区分结果。导出内容可为 `str`、`bytes` 或返回它们的
函数；写入采用临时文件、`fsync` 和原子替换，失败不会破坏已有目标文件。

## AsyncImage

```python
from aui import AsyncImage, Size

avatar = AsyncImage(
    "https://example.com/avatar.png",
    size=Size(160, 160),
)
```

`AsyncImage` 在后台线程使用标准库 `urllib` 加载，不阻塞 AppKit 事件循环。
`phase` 是 `AsyncImagePhase`，包含 `empty`、`success`、`failure` 状态以及成功的
`data` 或失败的 `error`。相同 URL 的默认请求会去重并共享进程内缓存；可用
`AsyncImage.clear_cache()` 清理。测试或自定义协议可注入 `loader(url) -> bytes`。

### Image 图片源与缩放

```python
symbol = Image(system_name="star.fill", color=Color.yellow, label="收藏")
local = Image.from_file(Path("cover.png"), size=Size(320, 180)).scaled_to_fit()
memory = Image.from_data(png_bytes, size=Size(320, 180)).scaled_to_fill()
```

`Image` 一次只接受一个来源：`system_name`、`path` 或 `data`。链式
`resizable()`、`scaled_to_fit()`、`scaled_to_fill()` 返回新视图，不修改原对象；
`rendering_mode("template")` 使用强调色着色，`original` 保留原图颜色。
`label` 提供辅助功能名称；纯装饰图使用 `decorative=True` 从辅助树隐藏。

## ObservedObject、StateObject 与环境

```python
@observable
class Model:
    count = 0

model = StateObject(Model)

def content(value):
    return VStack([
        Text(f"Count: {value.count}"),
        Button("+", lambda: setattr(value, "count", value.count + 1)),
    ]).on_change(value.count, changed, key="count")

view = EnvironmentReader(EnvironmentObject(Model), content) \
    .environment_object(model.value)
```

`StateObject` 延迟创建并拥有一个模型；`ObservedObject` 包装外部模型，两者都提供
`binding("attribute")`。AppKit 在执行视图工厂和环境 reader 时记录实际读取的
`@observable` 属性，只订阅本次构建依赖，下一次构建或关窗时自动解除旧订阅。

`.environment(key, value)` 按视图子树传播且允许内层覆盖；
`.environment_object(model)` 按具体类型注入。`EnvironmentReader` 延迟构建内容，
可读取 `EnvironmentValue(key, default)` 或 `EnvironmentObject(Type)`；缺失必需的
环境对象会抛出明确的 `LookupError`。

`.on_change(value, action, initial=False, key=None)` 支持零参数、单个新值参数或
`(old, new)` 回调。视图工厂中创建的修饰符建议提供稳定 `key`，以跨重建保存旧值。

## AppStorage 与 SceneStorage

```python
from pathlib import Path
from aui import AppStorage, JSONStore, SceneStorage

store = JSONStore(Path.home() / ".my_app" / "settings.json")
theme = AppStorage("theme", "system", store=store)
draft = SceneStorage("draft", "", scene_id="editor-window")

theme.value = "dark"
field = TextField(draft.binding(), "草稿")
```

`AppStorage` 与 `State` 使用相同的 `value`、`wrapped_value` 和 `binding()` 接口。
默认后端是进程内、线程安全的 `MemoryStore`，因此不会隐式写入用户磁盘；需要跨次
启动保留时，显式传入 `JSONStore(path)`。JSON 存储只接受可 JSON 序列化的值，
创建父目录后通过临时文件原子替换，写入失败会恢复内存中的旧值。

`SceneStorage` 按 `scene_id` 隔离，只保留当前进程中对应窗体会话的状态，适合导航
位置、选择项和未提交草稿，不等同于永久存储。

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

ProgressView(value=0.5, label="加载中").tint(Color.green)  # 确定进度
ProgressView()                            # 不确定进度（动画）
```

### Label（标题 + 图标）

```python
from aui import Label

Label("首页", system_name="house")
Label("邮件", system_name="envelope")
```

### badge（徽章修饰器）

```python
from aui import Label, Text

Text("Inbox").badge(3)
Label("Messages", system_name="envelope").badge("New")
```

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

列表也支持 SwiftUI 风格的稳定 ID 单选/多选、编辑模式、删除/移动回调及行级操作：

```python
from aui import EditMode, List, ListRowAction, State, Text

selection = State(set())
editing = State(EditMode.ACTIVE)
rows = [
    Text("Inbox").id("inbox").swipe_actions([
        ListRowAction("Archive", archive),
        ListRowAction("Delete", delete, role="destructive"),
    ]),
    Text("Protected").id("protected").delete_disabled().move_disabled(),
]
view = List(rows, selection=selection.binding(), edit_mode=editing.binding(),
            on_delete=remove_indices, on_move=move_indices)
```

AppKit 将 row swipe actions 提供为对应的原生上下文菜单；curses 中 Enter 选择行，
`D` 删除，`K`/`J` 上移/下移，编辑命令受 `EditMode` 控制。

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

NavigationStack(Text("内容").navigation_title("设置"))
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
| `corner_radius(radius)` | 圆角 |
| `opacity(value)` | 透明度 0~1 |
| `hidden()` | 隐藏（尺寸归零） |
| `frame(width, height, alignment)` | 固定尺寸 |
| `on_tap_gesture(action)` | 点击手势 |

修饰符可链式组合：

```python
from aui import Text, Color

Text("提示").padding(length=8).background(Color.blue).corner_radius(6)
```

## 动画（T19）

```python
from aui import Animation, Text, with_animation

# 1. 标记要动画化的视图
view = Text("Hello", color=Color.blue).animation(Animation.ease_in_out(0.4))

# 2. 在动画作用域内修改状态
with with_animation(Animation.ease_in_out(0.4)):
    state.wrapped_value = new_value
```

- `Animation.linear(d)` / `ease_in(d)` / `ease_out(d)` / `ease_in_out(d)` / `spring(d, damping)`
- `with_animation(anim)`：上下文管理器，包裹状态变更
- curses / ASCII 后端：动画作为声明式元数据保留（状态变化即时重渲染）
- 详见 [ADR-0006](adr/0006-animation.md)

## 手势（Gestures）

声明式手势修饰符，由渲染后端检测原生事件并触发回调。手势不影响布局。

| 手势 | 修饰符 | 回调签名 | 触发方式 |
|---|---|---|---|
| 点击 | `view.on_tap_gesture(action)` | `() -> None` | 单击 |
| 长按 | `view.on_long_press_gesture(action, minimum_duration=0.5)` | `() -> None` | 按住超过时长 |
| 拖拽 | `view.on_drag_gesture(action, minimum_distance=10.0)` | `(start, current) -> None` | 拖动超过最小距离 |

```python
from aui import Text, Color

# 点击
Text("Tap").padding().background(Color.blue).on_tap_gesture(on_tap)

# 长按（按住 0.6s 触发）
Text("Hold").on_long_press_gesture(on_hold, minimum_duration=0.6)

# 拖拽（回调收到起点与当前点）
def moved(start, current):
    print(f"dx={current.x - start.x}")

Text("Drag").on_drag_gesture(moved)
```

- curses 后端：`Tab/↑/↓` 移动焦点，`Enter` 激活选中的 tappable 区域（或按钮/开关），`←/→` 调整滑块/下拉/步进器/日期
- 详见 [ADR-0007](adr/0007-gestures.md)

## 可访问性（T25）

声明式可访问性修饰符，让界面可被屏幕阅读器等辅助技术描述与操作。
修饰符不影响布局，可链式组合。

| 修饰符 | 说明 |
|---|---|
| `view.accessibility_label(label)` | 元素的短名称 |
| `view.accessibility_hint(hint)` | 执行操作的结果描述 |
| `view.accessibility_value(value)` | 元素的当前值 |
| `view.accessibility_hidden(hidden=True)` | 从可访问性树排除（含子元素） |
| `view.accessibility_element(children=...)` | 子元素策略：`contain` / `combine` / `ignore` |

```python
from aui import (
    Button, Text, VStack,
    accessibility_label, accessibility_hint, accessibility_value,
    accessibility_hidden, accessibility_element, CHILDREN_COMBINE,
)

# 为按钮提供屏幕阅读器标签
Button("X", action=close).accessibility_label("关闭窗口")

# 提供提示与当前值
Button("保存", action=save).accessibility_hint("保存你的更改")
Text("50%").accessibility_value("百分之五十")

# 隐藏装饰性元素
Text("装饰").accessibility_hidden()

# 将子元素合并为单个可访问性元素
HStack([Text("姓名"), Text("张三")]).accessibility_element(CHILDREN_COMBINE)
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

- `CursesBackend.describe_accessibility()`：返回当前视图的可访问性树（终端/无头）
- `AsciiBackend.describe_accessibility(view)`：无头检查
- 详见 [ADR-0010](adr/0010-accessibility.md)

## 过渡与时间线动画

`Transition` 支持 opacity、scale、slide、edge move、组合和非对称过渡；
`ContentTransition` 与 `SymbolEffect` 描述内容及 SF Symbol 的变化效果。
`PhaseAnimator` 用离散阶段构建视图，`KeyframeAnimator` 则根据各关键帧时长、
曲线和目标值确定性插值。这些描述在无头后端也可以测试和渲染。

```python
phase = PhaseAnimator(["idle", "active"], lambda value: Text(value))
timeline = KeyframeAnimator(0.0, [Keyframe(1.0, 0.3)],
                            lambda value: Text(f"{value:.2f}"))
```

### 动画事务与几何匹配

`Animation` 支持 `.delay()`、`.speed()`、`.repeat_count()` 和
`.repeat_forever()`。`Transaction` / `with_transaction` 可随状态变更携带动画、
连续性或禁用动画策略；`.transaction()` 可在视图子树中调整策略。

```python
namespace = Namespace.create()
card = Text("Card").matched_geometry_effect("hero", namespace)

with with_transaction(Transaction(Animation.spring())):
    expanded.wrapped_value = True
```

`.accessibility_reduce_motion()` 会通过环境向下传播，并清除子树中的动画，
用于遵循减少动态效果的可访问性偏好。

## 视觉变换与图层合成

视图可使用 `.scale_effect()`、`.rotation_effect()` 和
`.rotation_3d_effect()` 做不改变布局尺寸的视觉变换。滤镜包括 `.blur()`、
`.brightness()`、`.contrast()`、`.saturation()`、`.grayscale()` 和
`.hue_rotation()`。

`.blend_mode()`、`.compositing_group()`、`.drawing_group()`、`.clipped()`、
`.clip_shape()` 与 `.mask()` 控制图层合成和裁剪。AppKit 后端使用 Core
Animation/Core Image 原生实现；终端和 ASCII 后端保持内容可读并安全忽略像素效果。

```python
card = (Text("Card")
        .rotation_3d_effect(8, axis=(1, 0, 0))
        .clip_shape(RoundedRectangle(16))
        .shadow(radius=10)
        .drawing_group())
```

## Canvas 与 TimelineView

`Path` 记录 move、line、二次/三次贝塞尔、矩形、椭圆和闭合路径。
`GraphicsContext` 使用 `fill` / `stroke` 产生绘图命令，`StrokeStyle` 控制线宽、
端点、连接、miter 和虚线。`Canvas` 在 AppKit 中转换为 `CGPath` 与
`CAShapeLayer`，无需第三方绘图库。

```python
def draw(context, size):
    path = Path.ellipse(Rect(Point(), size))
    context.fill(path, Color.blue)
    context.stroke(path, Color.white, StrokeStyle(3, "round", "round"))

canvas = Canvas(draw, width=240, height=160)
```

`TimelineView` 通过 `TimelineContext(date, cadence)` 构建时间相关内容；
`.tick(date)` 可推进到明确时间，因此快照测试和不同后端得到相同结果。

## AttributedString 与高级排版

`AttributedString` 保存文本和属性区间；`AttributedString.markdown()` 使用原生
Python 解析粗体、斜体、行内代码和链接。`Text` 可以直接接收该对象。

排版修饰器包括 `.kerning()`、`.tracking()`、`.baseline_offset()`、
`.text_case()`、`.multiline_text_alignment()`、`.truncation_mode()`、
`.minimum_scale_factor()`、`.allows_tightening()`、`.monospaced_digit()` 和
`.text_selection()`。这些属性支持容器继承和子视图覆盖。

```python
Text(AttributedString.markdown("**Hello** [Python](https://python.org)")) \
    .tracking(0.8).text_selection()
```

## 本地化与 Dynamic Type

`LocalizedStringKey` 包含 key、默认文案、语言映射和格式参数；`.locale()` 在
环境中选择准确区域或语言级回退。`.layout_direction("rightToLeft")` 会反转
水平布局的视觉顺序。

`DynamicTypeSize` 提供从 `xSmall` 到 `accessibility5` 的字号等级，
`.dynamic_type_size()` 会同时影响文本测量、换行和 AppKit 原生字体。

`.redacted()` 生成占位或隐私骨架文本，`.privacy_sensitive()` 标记敏感子树，
`.help()` 在 AppKit 映射为原生 tooltip。

```python
Text(LocalizedStringKey("welcome", "Welcome", {"zh": "欢迎"})) \
    .dynamic_type_size(DynamicTypeSize.ACCESSIBILITY1)
```

## 高级可访问性

除 label、hint、value、hidden 和 children 组合策略外，还支持：

- `.accessibility_add_traits()` / `.accessibility_remove_traits()`
- `.accessibility_sort_priority()`：实际重排同级辅助技术节点
- `.accessibility_identifier()`、`.accessibility_heading()`
- `.accessibility_input_labels()`、`.accessibility_custom_content()`
- `.accessibility_action()`、`.accessibility_adjustable_action()`

`AccessibilityInfo.perform_action()` 和 `.adjust()` 让无头测试能验证动作行为；
AppKit 同步设置原生 label、help、value、identifier、排序和输入标签属性。

## PreferenceKey 上行数据流

`PreferenceKey` 让子视图向祖先报告数据，与 Environment 的向下传播方向相反。
子类定义 `default_value` 和 `reduce()`；多个兄弟节点会按树顺序归并。

```python
class TotalKey(PreferenceKey):
    default_value = 0
    @classmethod
    def reduce(cls, value, next_value):
        return value + next_value

view = VStack([
    Text("A").preference(TotalKey, 2),
    Text("B").preference(TotalKey, 3),
]).on_preference_change(TotalKey, update_total)
```

`.transform_preference()` 可在中间容器修改聚合结果；框架会在渲染阶段读取
任意已收集子树。三套后端都会在渲染前自动收集并仅通知发生变化的值。

## 高级手势组合

提供 `TapGesture`、`SpatialTapGesture`、`MagnifyGesture`、`RotateGesture`，并与
已有 `DragGesture`、`LongPressGesture` 共享 changed/ended/updating 生命周期。
`GestureState` 在手势结束后自动恢复初始值。

手势可通过 `.simultaneously()`、`.sequenced()`、`.exclusively()` 组合；
视图使用 `.gesture()`、`.high_priority_gesture()` 或
`.simultaneous_gesture()` 设置优先级和命中范围。AppKit 点击手势使用原生
`NSClickGestureRecognizer`，终端可通过聚焦激活进入相同生命周期。

## Transferable 与拖放

`Transferable` 模型通过 `DataRepresentation` / `FileRepresentation` 声明导入、
导出方式。`UTType` 提供 data、text、plain text、JSON、URL、file URL、image、
PNG 和 JPEG，并支持类型符合关系。

```python
class Card(Transferable):
    transfer_representations = (
        DataRepresentation(UTType.JSON, encode_card, decode_card),
    )

source = Text("Card").draggable(Card("Inbox"))
target = Text("Drop").drop_destination(Card, accept_cards, is_targeted)
```

`DropInfo` 可查询载荷类型；后端使用统一的解码和目标状态
流程，便于无头测试自定义模型、纯文本、bytes、Path 和 JSON 数据。

## FormatStyle

`Text(value, format=style)` 保存原始值，并在渲染时根据环境 Locale 格式化。
提供：

- `NumberFormatStyle.number()`：precision、grouping、sign 与解析
- `NumberFormatStyle.percent()` / `.currency(code)`
- `DateFormatStyle(date_style, time_style)`
- `ListFormatStyle()`
- `ByteCountFormatStyle(binary=False)`

```python
view = VStack([
    Text(1234.5, format=NumberFormatStyle.number().precision(2)),
    Text(0.42, format=NumberFormatStyle.percent()),
    Text(total, format=NumberFormatStyle.currency("EUR")),
]).locale("de-DE")
```

`ParseableFormatStyle.parse()` 可把区域化数字、百分比、货币或日期文本恢复为值。

### 类型安全 TextField

`TextField(value=binding, format=parseable_style)` 将类型化 Binding 显示为区域化
文本，并在编辑时解析回模型。失败时保留原模型值，通过 `validation_error`
暴露错误；AppKit 会显示红色文字和 tooltip。

```python
TextField(
    placeholder="Amount",
    value=amount.binding(),
    format=NumberFormatStyle.currency("EUR"),
).text_field_style(TextFieldStyle.ROUNDED_BORDER)
```

`TextFieldStyle` 提供 `AUTOMATIC`、`PLAIN`、`ROUNDED_BORDER` 和
`SQUARE_BORDER`，支持容器继承与子字段覆盖。

## 上下文菜单、Hover 与感官反馈

`.context_menu(Menu(...))` 在 AppKit 映射为原生右键 `NSMenu`；`.on_hover()`
使用 `NSTrackingArea` 报告进入/离开，`.hover_effect()` 提供 automatic、highlight、
lift。`.content_shape()` 描述 interaction、hover、drag preview 或 context-menu
preview 的命中形状，`.allows_hit_testing(False)` 关闭交互。

`SensoryFeedback` 支持 success、warning、error、selection、impact、increase、
decrease、start、stop、alignment 和 levelChange。`.sensory_feedback()` 依据 trigger
变化和可选 condition 触发；AppKit 优先使用原生 haptic，不支持时降级为系统提示音。

## 容器与列表行样式

容器样式包括：

- `ListStyle`：automatic、plain、inset、grouped、insetGrouped、sidebar
- `FormStyle`：automatic、grouped、columns
- `GroupBoxStyle`：automatic、plain、card
- `DisclosureGroupStyle`：automatic、compact、card

列表行支持 `.list_row_background()`、`.list_row_separator()`、
`.list_row_insets()`、`.swipe_actions()`、`.delete_disabled()` 和
`.move_disabled()`；insets 会参与真实测量和放置。Section 支持
`.section_spacing()` 与 `.header_prominence()`。AppKit 根据 grouped/sidebar/card
样式绘制原生分组表面、背景和 separator。

## Searchable 搜索体验

`.searchable()` 是结构化容器，会组合后端原生搜索框、可选的分段样式 `Picker`
control、tokens、动态 suggestions 和原内容。支持 automatic、toolbar、sidebar、
navigationBarDrawer placement。

```python
view = List(rows).searchable(
    query.binding(), prompt="Search",
    suggestions=lambda text: matching_items(text),
    scopes=["All", "Unread"], scope=scope.binding(),
    tokens=[SearchToken("docs", "Docs")],
    on_submit=perform_search,
)
```

`SearchableView.submit()` 触发搜索提交，`dismiss_search()` 会清空查询并关闭可选
presentation Binding。AppKit 自动使用 `NSSearchField` 与原生 segmented control。

## 异步 task 与 refreshable

`.task(action, task_id=..., priority=..., key=...)` 在视图生命周期中启动同步或
async callable。`TaskHandle` 暴露 pending/running/success/failure/cancelled phase、
result、error、订阅、wait 和 cooperative cancel。

相同树位置/key 和 task id 会复用任务；id 改变时旧任务取消、新任务启动。
AppKit 在任务完成后调度主线程刷新，并在窗口关闭时取消存活任务。

`.refreshable(action)` 创建 `RefreshAction`；动作通过系统刷新交互触发，并可通过
`is_refreshing`/`latest` 检查状态。

## 系统环境与动作

`EnvironmentReader(scene_phase, ...)`、`color_scheme` 与
`control_active_state` 分别读取窗口生命周期、明暗模式和活动状态。
`.preferred_color_scheme(ColorScheme.DARK)` 可作用域覆盖外观；AppKit 会在窗口
获焦、失焦和最小化时刷新环境。

`open_url` 和 `dismiss` 是可调用环境值。`.open_url_action(handler)` 可拦截、
丢弃或重定向 URL，`Link` 自动遵循该策略；`.dismiss_action(callback)` 可为嵌套
视图注入关闭行为，AppKit 根环境默认关闭当前窗口。

## SwiftUI 控件样式

控件样式是可继承的视图修饰器，可施加到单个控件或整个容器：

```python
view = VStack([
    Button("Save", save).button_style(ButtonStyle.BORDERED_PROMINENT),
    Button("Cancel", cancel).button_style(ButtonStyle.PLAIN),
]).tint(Color.blue).control_size(ControlSize.LARGE)
```

支持 `ButtonStyle`、`ToggleStyle`、`PickerStyle`、`LabelStyle`、
`ProgressViewStyle`，以及 `.tint()`、`.control_size()`、`.disabled()`、
`.labels_hidden()`。子视图显式设置的样式优先于容器继承值。

`ControlGroup([controls], label=...)` 将相关按钮组织成紧凑操作组，支持
`ControlGroupStyle.AUTOMATIC`、`NAVIGATION`、`COMPACT_MENU`，并继承 tint、
control size 和 disabled 状态。AppKit 绘制连体面板表面，终端后端保留分组边界。

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
