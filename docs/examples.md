# 示例索引

新增样式示例：`examples/styles_appkit.py` 展示 SwiftUI 风格的控件样式、
强调色、控件尺寸与继承作用域。

`examples/advanced_animation_appkit.py` 展示过渡、符号效果、阶段动画和
关键帧时间线。

`examples/transaction_geometry_appkit.py` 展示动画事务、共享几何命名空间和
连续动画策略。

`examples/rendering_effects_appkit.py` 展示 Core Animation 变换、Core Image
滤镜、裁剪和图层合成。

`examples/canvas_timeline_appkit.py` 展示矢量 Path、Canvas 原生绘图和
TimelineView 时间内容。

`examples/typography_appkit.py` 展示 AttributedString、Markdown、原生文本
排版、截断和选择。

`examples/localization_dynamic_type_appkit.py` 展示本地化、Dynamic Type、
隐私 redaction 和原生帮助提示。

`examples/accessibility_advanced_appkit.py` 展示 traits、标题、自定义内容、
语音输入标签和可调节动作。

`examples/preferences_appkit.py` 展示 PreferenceKey、兄弟节点 reduce、中间变换
和祖先变化回调。

`examples/advanced_gestures_appkit.py` 展示 GestureState、缩放/旋转、双击和
同时/高优先级手势组合。

`examples/transferable_appkit.py` 展示自定义 Transferable、JSON representation、
draggable 和类型安全 drop destination。

`examples/format_styles_appkit.py` 展示 Locale 驱动的数字、百分比、货币、日期、
列表和字节大小格式化。

`examples/formatted_textfield_appkit.py` 展示类型安全 Binding、区域化输入解析、
错误反馈和原生 TextFieldStyle。

`examples/interaction_feedback_appkit.py` 展示原生右键菜单、hover tracking、
content shape、hit testing 和 sensory feedback。

`examples/container_styles_appkit.py` 展示 List/Form/GroupBox 样式、列表行背景、
insets、separator 和 Section 排版。

`examples/searchable_appkit.py` 展示原生搜索框、动态建议、搜索 scopes、tokens、
提交和 dismiss search。

`examples/async_lifecycle_appkit.py` 展示 async task、task id、自动完成刷新、
refreshable 和 TaskHandle 生命周期。

`examples/system_environment_appkit.py` 展示 ScenePhase、ColorScheme、环境
dismiss、作用域外观覆盖，以及遵循 OpenURLAction 策略的 Link。

`examples/scroll_reader_appkit.py` 展示 ScrollViewReader、稳定 ID、滚动位置
Binding、指示器、content margins 与 view-aligned 目标行为。

`examples/keyboard_focus_appkit.py` 展示原生 Return/Escape 快捷键、默认焦点、
FocusState 与焦点分区。

`examples/presentation_detents_appkit.py` 展示 medium/large detent、选择 Binding、
拖动指示器、圆角、交互式关闭控制和 full-screen cover。

`examples/navigation_split_appkit.py` 展示三栏 visibility Binding、preferred compact
column、prominent-detail 样式与逐列宽度约束。

`examples/window_configuration_appkit.py` 展示隐藏标题栏、固定内容尺寸、浮动窗口、
默认位置、尺寸范围与窗口 frame 恢复。

`examples/inspector_appkit.py` 展示 Binding 控制的 trailing Inspector、自定义列宽、
面板背景以及紧凑窗口下的自动覆盖布局。

`examples/control_group_appkit.py` 展示 navigation/automatic ControlGroup、组级标签、
统一控件尺寸和原生紧凑操作面板。

`examples/table_appkit.py` 展示原生多选、复合排序、可绑定列可见性、列宽约束和
空表状态。

`examples/outline_group_appkit.py` 展示原生 NSOutlineView、展开状态恢复、稳定节点
ID 和多选 Binding。

aUI 示例程序。所有示例均可从任意目录直接运行（内置路径引导）：

```bash
python3 examples/<name>.py
```

> 需要系统 Python 3.10+。curses 示例在终端中运行（`q` 退出）；
> ascii 示例无头渲染，直接打印文本。
> **aUI 使用标准库 curses 作为原生交互后端，不依赖 Tkinter / 显示服务器。**

## 交互式（curses 后端 · 原生）

| 示例 | 展示内容 | 运行 |
|---|---|---|
| [counter_curses.py](../examples/counter_curses.py) | 计数器：按钮 + 状态 | `python3 examples/counter_curses.py` |
| [form_curses.py](../examples/form_curses.py) | 设置表单：Form + 全部输入组件 | `python3 examples/form_curses.py` |
| [gallery_curses.py](../examples/gallery_curses.py) | 组件画廊：全部组件 | `python3 examples/gallery_curses.py` |
| [state_curses.py](../examples/state_curses.py) | 状态管理：ObservableObject / @observable | `python3 examples/state_curses.py` |
| [custom_curses.py](../examples/custom_curses.py) | 自定义组件：组合复用 | `python3 examples/custom_curses.py` |
| [showcase_curses.py](../examples/showcase_curses.py) | **全功能演示**：全部组件 + 布局 + SwiftUI 样式 + 手势 + 动画 + 状态 + 可访问性 + 自定义组件 | `python3 examples/showcase_curses.py` |

## 无头预览（ASCII 后端）

| 示例 | 展示内容 | 运行 |
|---|---|---|
| [counter_ascii.py](../examples/counter_ascii.py) | 计数器 ASCII 预览 | `python3 examples/counter_ascii.py` |
| [layout_ascii.py](../examples/layout_ascii.py) | 布局：VStack/HStack/Spacer/ZStack | `python3 examples/layout_ascii.py` |
| [preview_ascii.py](../examples/preview_ascii.py) | 完整设置界面预览 | `python3 examples/preview_ascii.py` |

> **说明**：Tkinter 后端已从 aUI 移除。aUI 的交互后端有两条原生路径：
> - **curses 终端窗口**（标准库，零依赖、无显示服务器）——任何终端均可运行；
> - **AppKit 原生 macOS 窗口**（PyObjC 调 Cocoa）——需要图形会话 + PyObjC。

## 原生窗口（AppKit 后端 · macOS）

| 示例 | 展示内容 | 运行 |
|---|---|---|
| [showcase_appkit.py](../examples/showcase_appkit.py) | **全功能演示**：全部组件以**原生 Cocoa 控件**呈现在 macOS 窗口中（NSButton / NSSwitch / NSSlider / NSPopUpButton / NSStepper / NSDatePicker / NSColorWell / NSProgressIndicator …），同一棵 `make_view()` 树 | `python3 examples/showcase_appkit.py` |
| [navigation_split_appkit.py](../examples/navigation_split_appkit.py) | 自适应三栏布局与多窗口场景 | `python3 examples/navigation_split_appkit.py` |
| [navigation_path_appkit.py](../examples/navigation_path_appkit.py) | 值驱动前进/返回与类型化目标视图 | `python3 examples/navigation_path_appkit.py` |
| [presentation_appkit.py](../examples/presentation_appkit.py) | 原生 Sheet、Alert、dismiss 与破坏性操作 | `python3 examples/presentation_appkit.py` |
| [commands_appkit.py](../examples/commands_appkit.py) | 标题栏 Toolbar、Menu、SF Symbols 与键盘快捷键 | `python3 examples/commands_appkit.py` |
| [table_appkit.py](../examples/table_appkit.py) | 原生 NSTableView、对象列、排序与选择绑定 | `python3 examples/table_appkit.py` |
| [visual_effects_appkit.py](../examples/visual_effects_appkit.py) | 原生渐变、Material、Overlay、Shadow 与 Shape | `python3 examples/visual_effects_appkit.py` |
| [structural_views_appkit.py](../examples/structural_views_appkit.py) | ForEach 身份、GroupBox、AnyView 与自适应 ViewThatFits | `python3 examples/structural_views_appkit.py` |
| [lazy_grid_appkit.py](../examples/lazy_grid_appkit.py) | Lazy Stack、adaptive GridItem 与身份复用 | `python3 examples/lazy_grid_appkit.py` |
| [scroll_reader_appkit.py](../examples/scroll_reader_appkit.py) | 稳定视图 ID、ScrollViewProxy 与锚点跳转 | `python3 examples/scroll_reader_appkit.py` |
| [focus_state_appkit.py](../examples/focus_state_appkit.py) | FocusState、first responder 与双向焦点绑定 | `python3 examples/focus_state_appkit.py` |
| [events_appkit.py](../examples/events_appkit.py) | onAppear/onDisappear、Return 提交与 submit label | `python3 examples/events_appkit.py` |
| [storage_appkit.py](../examples/storage_appkit.py) | AppStorage、SceneStorage 与原子 JSON 偏好存储 | `python3 examples/storage_appkit.py` |
| [geometry_reader_appkit.py](../examples/geometry_reader_appkit.py) | GeometryReader、坐标空间与宽度自适应布局 | `python3 examples/geometry_reader_appkit.py` |
| [outline_group_appkit.py](../examples/outline_group_appkit.py) | OutlineGroup 树形数据、稳定 ID 与展开状态绑定 | `python3 examples/outline_group_appkit.py` |
| [settings_scene_appkit.py](../examples/settings_scene_appkit.py) | 单实例 Settings 场景、SettingsLink、⌘, 与持久化偏好 | `python3 examples/settings_scene_appkit.py` |
| [lazy_windows_appkit.py](../examples/lazy_windows_appkit.py) | WindowLink、场景 ID 与按需单实例次级窗口 | `python3 examples/lazy_windows_appkit.py` |
| [menu_bar_extra_appkit.py](../examples/menu_bar_extra_appkit.py) | 原生 MenuBarExtra、SF Symbol、分隔项与快捷键 | `python3 examples/menu_bar_extra_appkit.py` |
| [application_commands_appkit.py](../examples/application_commands_appkit.py) | Commands、CommandMenu 与应用级原生菜单 | `python3 examples/application_commands_appkit.py` |
| [system_controls_appkit.py](../examples/system_controls_appkit.py) | 原生 ShareLink、PasteButton、共享服务与剪贴板 | `python3 examples/system_controls_appkit.py` |
| [file_dialogs_appkit.py](../examples/file_dialogs_appkit.py) | 原生文件导入/导出面板、过滤、多选与原子写入 | `python3 examples/file_dialogs_appkit.py` |
| [async_image_appkit.py](../examples/async_image_appkit.py) | AsyncImage 阶段、后台加载、缓存与原生 NSImage | `python3 examples/async_image_appkit.py` |
| [image_sources_appkit.py](../examples/image_sources_appkit.py) | SF Symbol、本地/内存图片、fit/fill 与模板模式 | `python3 examples/image_sources_appkit.py` |
| [observation_environment_appkit.py](../examples/observation_environment_appkit.py) | StateObject、EnvironmentObject、依赖追踪与 on_change | `python3 examples/observation_environment_appkit.py` |
| [custom_layout_appkit.py](../examples/custom_layout_appkit.py) | 自定义 Layout、AnyLayout、优先级与高级布局修饰符 | `python3 examples/custom_layout_appkit.py` |

```bash
# 前提：安装 PyObjC（Apple 官方桥接层，非 Tk）
python3 -m pip install pyobjc-framework-Cocoa

# 运行
python3 examples/showcase_appkit.py             # 打开原生窗口（⌘Q 退出）
python3 examples/showcase_appkit.py --check     # 仅报告可用性
```

窗口是**真正的 macOS 窗口**：所有控件都是原生 `NSControl`，双向绑定到 aUI 的
`State` / `Binding`（拖动滑块、切换开关、编辑输入框会实时写回状态）。视图树与
curses 示例共用 `examples/showcase_view.py`，保证两种后端展示完全一致。

## 一键运行（自动选择后端）

`run_showcase.py` 自动选择可用后端：有真实 TTY 就用 curses 交互窗口；否则自动
降级为无头文本渲染（同一视图树 + 可访问性层级）。在 macOS 图形会话中可用
`--appkit` 强制打开原生窗口：

```bash
python3 examples/run_showcase.py            # 自动选择：curses 窗口 → 文本降级
python3 examples/run_showcase.py --ascii    # 强制无头文本渲染
python3 examples/run_showcase.py --appkit   # 强制 macOS 原生窗口（需 PyObjC）
python3 examples/run_showcase.py --check    # 仅输出环境报告（各 Python / curses / appkit / TTY 状态）
python3 examples/run_showcase.py --python /path/to/python3   # 指定解释器
```

`showcase_curses.py` 自身也内置了同样的降级逻辑，可直接运行。

> **降级原因与建议**（输出中会明确打印原因）：
> - **stdin 非 TTY**（管道 / CI）：输出会显示 `stdin is not a TTY (piped/CI)`。
>   在真实终端里运行即可打开交互窗口。
> - **Python 过旧**：aUI 需要 ≥ 3.10。
> - curses 是 CPython 标准库（macOS/Linux 自带），一般无需安装。

## 交互控制（curses 示例通用）

| 按键 | 作用 |
|---|---|
| `Tab` / `↑` / `↓` | 在可交互组件间移动焦点 |
| `Enter` | 激活当前焦点（按钮 / 开关 / 点击区域） |
| `←` / `→` | 调整当前焦点的滑块 / 下拉 / 步进器 / 日期 |
| 打字 / `Backspace` | 编辑当前输入框 |
| `PageUp` / `PageDown` | 整页上下滚动（内容超高时） |
| `h` | 帮助 |
| `q` / `Q` | 退出 |
