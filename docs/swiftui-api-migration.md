# SwiftUI API 清理迁移

项目已删除早期 Bootstrap 风格兼容层。组件只保留 SwiftUI 能表达的语义，视觉
配置统一通过 View modifier 和环境样式完成。

| 已删除 API | SwiftUI 对齐写法 |
|---|---|
| `Button(role="success/primary/...")` | `Button(...).tint(Color.green)` |
| `Button(role="danger")` | `Button(..., role="destructive")` |
| `.variant(...)` | `.tint(...)` 或对应 control style |
| `.button_size("sm/md/lg")` | `.control_size(ControlSize.SMALL/REGULAR/LARGE)` |
| `.toggle_size(...)` | `.control_size(...)` |
| `.outlined()` | `.button_style(ButtonStyle.BORDERED)` |
| `.as_block()` | `.frame(width=...)` |
| `.as_pill()` | `.clip_shape(Capsule())` |
| `.with_shadow()` | `.shadow(...)` |
| `ProgressView.striped()` | `.progress_view_style(...)` |
| 独立 `Badge("New")` | `content.badge("New")` |
| 组件专属 `.disabled()` 副本方法 | 统一 `View.disabled()` 环境修饰器 |
| 构造器 `enabled=False` | `Component(...).disabled()` |
| `SegmentedControl(options, selection)` | `Picker("", selection=selection, options=options).picker_style(PickerStyle.SEGMENTED)` |
| 直接构造 `SearchField(...)` | 在内容视图上使用 `.searchable(text, prompt=...)` |
| `ToolbarItem(id, label, action, ...)` | `ToolbarItem(id, Button(label, action), placement=...)` |
| `NavigationStack(title, content, path=...)` | `NavigationStack(content.navigation_title(title), path=...)` |
| `padding(view)`, `background(view, ...)` 等顶层视觉函数 | `view.padding()`, `view.background(...)` 等实例修饰器 |
| `button_style(view, ...)`、`disabled(view)`、`badge(view, ...)` 等顶层函数 | 对应的 `view.button_style(...)`、`view.disabled()`、`view.badge(...)` |
| `frame(view, ...)`、`offset(view, ...)` 等顶层布局函数 | 对应的 `view.frame(...)`、`view.offset(...)` 实例修饰器 |
| 顶层渲染、文本和容器样式函数 | 对应的 `View` 实例修饰器 |
| 顶层导航、呈现和生命周期修饰器函数 | 对应的 `View` 实例修饰器 |
| 顶层环境、滚动、焦点、任务和文件对话框修饰器 | 对应的 `View` 实例修饰器 |
| 顶层转场、搜索、列表编辑和视觉效果修饰器 | 对应的 `View` 实例修饰器 |
| 顶层 Preference、拖放和交互反馈修饰器 | 对应的 `View` 实例修饰器 |
| 顶层手势与无障碍修饰器 | 对应的 `View` 实例修饰器 |
| `matched_geometry_effect(view, ...)`、`transaction(view, ...)`、`toolbar(view, ...)` | 对应的 `View` 实例修饰器 |
| 顶层解析器、状态收集器及后端模拟函数 | 移至 `aui.core` 内部模块，仅供框架与测试使用 |
| `AlertButton(...)` | alert 与 confirmation dialog 直接使用 `Button(...)` |
| `MenuItem(...)` / `MenuDivider()` | `Button(...)` / `Divider()`；快捷键使用 `.keyboard_shortcut(...)` |

`Button.role` 现在只接受 `None`、`"destructive"` 和 `"cancel"`。旧值会明确抛出
`ValueError`，不会静默映射颜色。

交互组件构造器不再接受 `enabled=`。禁用状态通过环境向下传播，因此容器上的
`.disabled(condition)` 会同时影响所有后代控件，和 SwiftUI 行为一致。

示例不再通过 `examples/_bootstrap.py` 修改 `sys.path`。请先以 editable 模式安装
项目（`python -m pip install -e .`），再直接运行 `python examples/<name>.py`。
