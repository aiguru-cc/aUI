# aUI

一个基于 Python 的 UI 库，用于快速创建简单的用户界面，完全复刻 SwiftUI 的
语法和功能。aUI 提供了基本的组件，如按钮、文本框、下拉列表等，以及一些
高级功能，如事件处理、样式设置、状态管理、动画、手势与可访问性。aUI 还
支持自定义组件，用户可以根据需要创建自己的组件。

## 特点

- **声明式**：用视图树描述 UI（SwiftUI 风格），非命令式操作控件。
- **零依赖**：原生交互后端基于标准库 `curses`，无第三方依赖、无显示服务器。
- **macOS 原生窗口**：AppKit 后端（PyObjC 调 Cocoa）把每个组件映射为原生
  `NSControl`，真正的 Cocoa 窗口，非 Tk。
- **应用级结构**：支持 `Window` / `WindowGroup` 多窗口场景，以及可自适应折叠的
  二栏、三栏 `NavigationSplitView`；`Settings` / `SettingsLink` 提供单实例偏好
  设置窗口和原生 `⌘,` 菜单入口，`WindowLink` / `DismissWindowLink` 可按 ID
  懒打开和关闭次级窗体，`MenuBarExtra` 创建原生 macOS 状态栏菜单。
- **几何感知布局**：`GeometryReader` / `GeometryProxy` 提供尺寸、安全区以及 local、
  global 坐标框架，用于随窗口宽度切换布局。
- **可扩展布局协议**：`Layout`、`LayoutSubview`、`LayoutPlacement` 与 `AnyLayout`
  支持自定义放置算法和运行时布局切换，并读取子视图 `layout_priority`。
- **值驱动导航**：`NavigationPath`、`NavigationLink` 和类型化
  `navigation_destination` 支持前进、返回及可测试的导航状态。
- **原生呈现**：SwiftUI 风格 `.sheet()`、`.alert()`、`.popover()` 和
  `.confirmation_dialog()` 映射到 macOS 原生呈现控件，支持 dismiss 和按钮角色。
- **系统服务**：`ShareLink` 调用 macOS 原生共享服务，`PasteButton` 从系统
  剪贴板读取文本并写回 `Binding`；`.file_importer()` / `.file_exporter()` 使用
  原生文件面板和原子写入。
- **异步图片**：`AsyncImage` 提供 empty/success/failure 阶段、后台加载、请求
  去重和内存缓存，AppKit 成功后呈现原生 `NSImage`。
- **完整图片源**：`Image` 支持 SF Symbol、本地路径和内存字节，并提供
  `resizable`、fit/fill、模板着色与装饰图片语义。
- **命令系统**：`Menu`、`.toolbar()`、`ToolbarItem` 和 `KeyboardShortcut`
  映射到原生菜单项、标题栏控件与快捷键；`Commands` / `CommandMenu` 声明
  应用级 macOS 主菜单。
- **数据视图**：`Table` / `TableColumn` 支持对象或字典数据、列值闭包、
  `SortOrder` 排序与选择绑定，AppKit 映射为原生 `NSTableView`。
- **原生视觉效果**：线性/径向渐变、Material、Shadow、Overlay、Capsule 与
  Ellipse 使用 Core Animation 和 AppKit Visual Effect 实现。
- **结构型视图**：`ForEach` 保持数据身份，`ViewThatFits` 自适应候选布局，
  `OutlineGroup` 展示可绑定展开状态的树形数据，并提供 `AnyView`、`EmptyView`
  与 `GroupBox`。
- **延迟布局**：`LazyVStack`、`LazyHStack`、`LazyVGrid`、`LazyHGrid` 与
  fixed/flexible/adaptive `GridItem` 延迟构建并复用数据视图，支持轨道级 spacing
  与 alignment。
- **程序化滚动**：`ScrollViewReader`、`ScrollViewProxy` 和 `.id()` 支持按稳定
  视图标识跳转到 top/center/bottom 锚点。
- **声明式焦点**：`FocusState` 与 `.focused()` 双向同步 AppKit first responder
  和 curses 键盘焦点。
- **生命周期与提交**：`.on_appear()` / `.on_disappear()` 和 `.on_submit()` /
  `.submit_label()` 覆盖视图出现、离开及表单 Return 行为。
- **SwiftUI 内容结构**：支持跨行对齐的 `Grid/GridRow`、`LabeledContent`、
  `ContentUnavailableView`、基础 Shape 和原生 SF Symbols。
- **状态驱动**：`State` / `Binding` / `ObservableObject` / `@observable` /
  `Environment` 变化自动触发重渲染。
- **观察与依赖注入**：`ObservedObject`、`StateObject`、`EnvironmentObject`、
  `EnvironmentReader` 和 `.on_change()` 支持按读取依赖订阅、作用域覆盖与自动释放。
- **状态持久化**：`AppStorage`、`SceneStorage`、线程安全 `MemoryStore`，以及显式路径、
  原子写入的纯标准库 `JSONStore`。
- **SwiftUI 控件语义**：交互组件支持 focused/disabled 状态；Button 使用
  destructive/cancel 语义角色以及 buttonStyle、controlSize 和 tint。
- **可测试**：布局与状态逻辑可在无显示环境运行（`AsciiBackend` / curses 无头渲染）。

## 快速开始

```bash
# 终端交互窗口（curses，零依赖）
python3 examples/run_showcase.py

# macOS 原生窗口（AppKit，需 PyObjC）
python3 -m pip install pyobjc-framework-Cocoa
python3 examples/showcase_appkit.py

# 全功能演示：全部组件 + 布局 + 修饰符 + 手势 + 动画 + 状态 + 可访问性 + 自定义组件
python3 examples/showcase_curses.py
```

AppKit 后端默认采用跟随浅色/深色模式的 SwiftUI 风格主题（语义色、圆角卡片、
圆角输入框与统一强调色），也可以只用原生 Python 对象定制：

```python
from aui import Color
from aui.backends.appkit import AppKitBackend, AppKitTheme

theme = AppKitTheme().with_accent(Color.indigo)
AppKitBackend(make_view, theme=theme).run(title="My App")
```

控件树支持可继承的 SwiftUI 风格修饰器：

```python
VStack([
    Button("Save", save).button_style(ButtonStyle.BORDERED_PROMINENT),
    Toggle("Sync", sync_binding),
]).tint(Color.indigo).control_size(ControlSize.LARGE)
```

包括 `ButtonStyle`、`ToggleStyle`、`PickerStyle`、`LabelStyle`、
`ProgressViewStyle`、`disabled` 与 `labels_hidden`。

动画层提供组合/非对称 `Transition`、`ContentTransition`、`SymbolEffect`、
阶段式 `PhaseAnimator` 与可按时间求值的 `KeyframeAnimator`。
同时支持 `Transaction`、delay/speed/repeat、`matched_geometry_effect` 和
减少动态效果环境策略。

视觉层提供 scale/rotation/3D rotation、模糊与颜色滤镜、混合模式、
绘制分组、形状裁剪和遮罩，并由 AppKit 原生图层渲染。

绘图层提供 `Path`、`GraphicsContext`、`StrokeStyle`、原生 `Canvas` 和
可确定性推进的 `TimelineView`。

文本层支持 `AttributedString`、轻量 Markdown、字距、基线、多行对齐、
截断、缩放、等宽数字和原生文本选择。

自适应层支持 `LocalizedStringKey`、Locale、RTL 布局、Dynamic Type、
redaction、隐私敏感标记和原生帮助提示。

高级可访问性支持 traits、标题级别、排序优先级、稳定标识符、自定义内容、
语音输入标签、命名动作和可调节动作。

数据流同时支持 Environment 向下传播和 `PreferenceKey` 向上聚合，包含 reduce、
transform 与变化监听。

手势层支持 tap/spatial tap、drag、long press、magnify、rotate、临时
`GestureState`，以及 simultaneous/sequence/exclusive/高优先级组合。

数据传输层支持 `Transferable`、UTType、Data/File representation、draggable、
类型安全 drop destination 和无头拖放模拟。

格式化层支持 `Text(value, format=...)`、数字/百分比/货币、日期、列表和字节
格式，以及区域化 parse roundtrip。

表单字段支持 `TextField(value=binding, format=...)` 类型化输入、解析错误恢复，
以及 plain/rounded/square 原生样式。

交互反馈层支持原生 context menu、hover tracking/effect、content shape、hit
testing 与 haptic/system-beep sensory feedback。

Shape 层支持 `UnevenRoundedRectangle` 四角独立半径、`inset()` 和内描边
`stroke_border()`；完整 `StrokeStyle` 可控制 cap/join/miter/dash，AppKit 使用
`CAShapeLayer` 路径原生绘制，并支持 `.trim()` 路径区间与 `FillStyle`。

渐变层支持 `LinearGradient`、带起止半径的 `RadialGradient`、
`EllipticalGradient` 与原生 conic `AngularGradient`，并提供确定性的色标插值采样。

图片层支持缩放模式、插值和抗锯齿，以及 SF Symbol variants 与
monochrome/hierarchical/palette/multicolor 原生渲染模式、image scale、weight
和 cap-inset 九宫格拉伸/平铺，并支持 0...1 的 variable SF Symbols。

容器层支持 List/Form/GroupBox/DisclosureGroup 样式、列表行背景/insets/separator、
稳定 ID 单选/多选、EditMode、删除/移动和 row swipe actions，以及 Section spacing
与 header prominence。

搜索层支持 `.searchable()`、原生 NSSearchField、placement、动态 suggestions、
scopes、tokens、submit 和 dismiss search。

异步层支持 `.task()`、id 重启、优先级、取消、结果阶段、`.refreshable()` 和
AppKit 完成后的主线程刷新。

系统环境层支持 `ScenePhase`、`ColorScheme`、`ControlActiveState`，以及可注入的
`OpenURLAction` / `DismissAction`。AppKit 会随窗口激活、失焦、最小化更新环境，
`Link` 遵循作用域内的 URL 策略，`.preferred_color_scheme()` 可覆盖窗口外观。

导航目的地支持 `.navigation_title()`、inline/large 标题模式、导航栏隐藏与背景
覆盖；路径前进和返回时会自动切换并恢复对应页面的导航配置。

滚动层支持指示器可见性、默认滚动锚点、content margins、裁剪策略、paging/
view-aligned 目标行为，以及基于稳定 ID Binding 的 `.scroll_position()`。

键盘层支持视图级快捷键、Return 默认动作、Escape 取消动作、默认焦点、焦点分区
和可拦截的 `.on_key_press()`；AppKit 与 curses 共享相同事件语义。

呈现层支持 full-screen cover、medium/large/固定/比例 detent、detent 选择 Binding、
拖动指示器、交互关闭控制、背景交互策略与呈现圆角。

三栏导航支持列可见性 Binding、preferred compact column、balanced/
prominent-detail 样式和逐列宽度约束，所有后端共享相同折叠决策。

Scene 层支持窗口样式、content-size resizability、默认屏幕位置、尺寸范围、浮动
层级和 frame restoration 标识，并映射到原生 NSWindow。

Inspector 支持 Binding 显隐、trailing 辅助列宽约束、原生面板背景/分隔线，并在
紧凑宽度自动切换为覆盖式属性面板。

ControlGroup 支持相关操作的紧凑分组、navigation/compact-menu 样式，以及 tint、
control size、disabled 等样式的组内继承。

Table 支持 set Binding 多选、稳定的多列排序、可绑定列可见性、列宽范围、交替行
背景和跨后端空状态，AppKit 映射到原生 NSTableView。

OutlineGroup 支持默认展开深度、批量展开/收起、可见节点遍历和单选/多选 Binding，
AppKit 映射为原生 NSOutlineView 并同步 disclosure 状态。

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

## 文档

- [架构](docs/architecture.md)
- [组件参考](docs/components.md)
- [使用指南](docs/guide.md)
- [示例索引](docs/examples.md)
- [基线任务](docs/tasks/BASELINE.md)
