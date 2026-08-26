# aUI 基线任务清单

本文件定义 aUI v0.1 的基线任务。每项含验收标准（AC）。
标记规则：`[x]` 已完成，`[ ]` 待办，`[~]` 进行中。

## 阶段 1：工程基础（已建立）

- [x] T1 初始化 git 仓库与 `.gitignore`
- [x] T2 建立 `pyproject.toml`（src 布局、dev 依赖）
- [x] T3 建立包结构 `src/aui/{core,backends}`

## 阶段 2：核心实现（已建立）

- [x] T4 几何原语：`Size/Point/EdgeInsets/Color/Font`
- [x] T5 `View` 协议与 `ViewModifier`（proposal/response 布局契约）
- [x] T6 状态管理：`State/Binding/ObservableObject/@observable/Environment`
- [x] T7 布局容器：`VStack/HStack/ZStack/Spacer`
- [x] T8 修饰符：`padding/background/foregroundColor/font/border/cornerRadius/opacity/hidden/frame/onTapGesture`
- [x] T9 组件：`Text/Button/TextField/Toggle/Slider/Picker/Image/Divider/List/Group`
- [x] T10 渲染后端：`AsciiBackend`（无头）、`TkBackend`（Tkinter）

## 阶段 3：验证与治理（已建立）

- [x] T11 单元测试（geometry/layout/state/components/ascii backend）
- [x] T12 示例（`examples/counter_ascii.py`、`examples/counter_tk.py`）
- [x] T13 ADR 文档（`docs/adr/0001-0003`）
- [x] T14 文档库（`docs/architecture.md`、`docs/components.md`、`docs/guide.md`）
- [x] T15 基线任务清单（本文档）
- [x] T16 协作系统计划任务（`.aiguru` task-create）

## 阶段 4：演进（待办）

- [ ] T17 增量渲染（视图身份 + diff 复用控件）— 对应 ADR-0003 演进项
- [ ] T18 精确文本测量与换行
- [ ] T19 动画与过渡
- [ ] T20 手势系统（拖拽、长按）
- [ ] T21 `List` 懒加载与滚动
- [ ] T22 更多后端（Qt / 终端）
- [ ] T23 更多 SwiftUI 组件（`Stepper`、`DatePicker`、`ProgressView`、`Form`、`NavigationStack`）
- [ ] T24 主题与动态类型支持
- [ ] T25 可访问性（accessibility）支持

## 验收标准说明

- 阶段 2 各组件：`from aui import *` 可用、可布局（`size_that_fits`）、可被后端渲染。
- 阶段 3：`pytest` 全绿；文档命令可复制执行。
- 阶段 4 每项：需先更新对应 ADR 或新增 ADR，再实现并测试。
