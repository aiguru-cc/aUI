# 示例索引

aUI 示例程序。所有示例均可从任意目录直接运行（内置路径引导）：

```bash
python3 examples/<name>.py
```

> 需要系统 Python 3.9+。curses 示例在终端中运行（`q` 退出）；
> ascii 示例无头渲染，直接打印文本。

## 交互式（curses 后端）

| 示例 | 展示内容 | 运行 |
|---|---|---|
| [counter_curses.py](../examples/counter_curses.py) | 计数器：按钮 + 状态 | `python3 examples/counter_curses.py` |
| [form_curses.py](../examples/form_curses.py) | 设置表单：Form + 全部输入组件 | `python3 examples/form_curses.py` |
| [gallery_curses.py](../examples/gallery_curses.py) | 组件画廊：全部 12 种组件 | `python3 examples/gallery_curses.py` |
| [state_curses.py](../examples/state_curses.py) | 状态管理：ObservableObject / @observable | `python3 examples/state_curses.py` |
| [custom_curses.py](../examples/custom_curses.py) | 自定义组件：组合复用 | `python3 examples/custom_curses.py` |

## 无头预览（ASCII 后端）

| 示例 | 展示内容 | 运行 |
|---|---|---|
| [counter_ascii.py](../examples/counter_ascii.py) | 计数器 ASCII 预览 | `python3 examples/counter_ascii.py` |
| [layout_ascii.py](../examples/layout_ascii.py) | 布局：VStack/HStack/Spacer/ZStack | `python3 examples/layout_ascii.py` |
| [preview_ascii.py](../examples/preview_ascii.py) | 完整设置界面预览 | `python3 examples/preview_ascii.py` |

## 原生窗口（Tkinter 后端）

| 示例 | 展示内容 | 运行 |
|---|---|---|
| [counter_tk.py](../examples/counter_tk.py) | 计数器 Tk 窗口 | `python3 examples/counter_tk.py` |
| [gestures_tk.py](../examples/gestures_tk.py) | 手势：点击/长按/拖拽 | `python3 examples/gestures_tk.py` |
| [animation_tk.py](../examples/animation_tk.py) | 动画：颜色过渡 | `python3 examples/animation_tk.py` |
| [showcase_tk.py](../examples/showcase_tk.py) | **全功能演示**：全部组件 + 布局 + 修饰符 + 手势 + 动画 + 状态 + 可访问性 + 自定义组件 | `python3 examples/showcase_tk.py` |

> Tk 示例需要 Python 编译 Tk 支持（`import tkinter` 可用）。

## 交互控制（curses 示例通用）

| 按键 | 作用 |
|---|---|
| `Tab` / `↑` / `↓` | 切换输入框焦点 |
| 打字 | 编辑当前输入框 |
| `Backspace` | 删除字符 |
| `Enter` | 确认输入框 / 激活选中的 tappable 区域 |
| `t` | 循环选中可点击区域（配合 Enter 激活） |
| `q` / `Q` | 退出 |
