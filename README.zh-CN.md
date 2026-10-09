# NuPhy Codex Sidelight

让键盘两侧的光跟随 Codex。用本地 React 控制台，把 NuPhy Air75 V3 侧灯变成编码助手的状态提示灯。

[English](README.md) · [MIT 许可证](LICENSE)

![NuPhy Codex Sidelight：连接检查、实时状态、自定义颜色与灯效](docs/images/preview.jpg)

## 能做什么

- **显示当前状态**：工作中、等待处理、本轮结束、运行异常与空闲。
- **检查连接**：检测 macOS、Codex 安装情况、键盘设备，并通过 USB 实际回读灯光配置。
- **逐个测试**：进入测试模式，观察每种状态的实物灯效，随后恢复自动联动。
- **自由配置**：每个状态独立设置颜色和原厂灯效，支持单项或全部恢复默认。
- **持久保存**：中英文切换、语言偏好、颜色和灯效在重启后保留。
- **本地运行**：无需账号、API Key、云服务或刷固件。

**已验证硬件：NuPhy Air75 V3 ANSI、原厂固件、Mac、USB 数据线与有线模式。** 两侧灯条显示同一状态。本版本不支持其他型号、ISO 配列、无线连接、Windows 或 Linux。

## 开始使用

需要 Node.js **24+**、Python **3.11+** 和 USB 数据线。自动联动需要支持 [Hooks](https://learn.chatgpt.com/docs/hooks) 的本地 Codex；可以先测试键盘，再开启联动。

```sh
git clone https://github.com/joe960913/nuphy-codex-sidelight.git
cd nuphy-codex-sidelight

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
npm run build
npm start
```

1. 连接键盘并切换到有线模式。关闭 NuPhy IO 配置窗口，避免争用设备连接。
2. 打开 **[127.0.0.1:8765](http://127.0.0.1:8765)**，点击「测试连接」。仅检测到接收器不算连接成功。
3. 进入测试模式，逐个测试状态。页面在键盘配置回读成功后才确认灯光变化。

### 启用 Codex 自动联动

在另一个终端进入同一项目目录，运行：

```sh
.venv/bin/python bridge.py install
```

安装会向 `~/.codex/hooks.json` 合并七项事件定义，保留其他 Hook，并将已有配置备份到 `runtime/`。启动 `codex`，输入 `/hooks`，审核并信任本项目的命令。命令应使用当前项目的 `.venv/bin/python` 执行 `bridge.py hook`。然后开启一轮新的本地 Codex 对话，确认控制台收到状态。

页面分别显示「事件已配置」和「已收到状态」。信任由用户控制，应用不会改写 Codex 的信任记录。安装后请保留项目路径；如果需要移动目录，先在原位置卸载 Hook，移动后重新安装并审核。

第一条 Hook 事件会自动启动灯光进程。安装后，自动联动无需一直打开浏览器或 Web 服务。默认空闲配置下，进程恢复原灯效，约 30 秒后退出；如果为空闲设置了自定义效果，进程会保持运行。

## 状态与灯效

| 状态 | 默认灯光 | 含义 |
| --- | --- | --- |
| 工作中 | 蓝色 · 呼吸 | Codex 正在思考或执行工具 |
| 等待处理 | 橙色 · 呼吸 | 等待批准或同步的用户回复 |
| 本轮结束 | 绿色 · 常亮 15 秒 | 本轮结束，不保证任务成功 |
| 运行异常 | 红色 · 呼吸 15 秒 | 本地任务异常退出 |
| 空闲 | 键盘原灯效 | 没有活动回合，或用户中断 |

每个状态可选 **呼吸、常亮、流水、霓虹、律动** 或 **键盘原灯效**。霓虹自动循环颜色，不使用固定颜色。「波浪」属于按键背光，侧灯的动态选项是「流水」。动画由键盘运行，应用不会连续发送动画帧。

选择颜色或输入六位 HEX，选定灯效后，点击该状态的「保存」。断开键盘时也能保存设置；设置已保存与设备已确认分别显示。当前状态的修改在设备可用时应用，其他状态在切换到该状态时应用。

**恢复默认**恢复应用预设的状态配置；**键盘原灯效**恢复接管前捕获的侧灯配置，不会将整把键盘恢复出厂，也不改动按键背光。恢复全部状态默认值会保留语言偏好。

多个本地聊天合并显示，优先级为：**异常 → 等待 → 工作中 → 本轮结束 → 空闲**。测试模式暂时覆盖自动状态，关闭测试页面后最多 20 秒恢复联动。异步提问没有可可靠清除等待状态的配对回复 Hook，因此不显示为持续等待。

## 本地数据与恢复

服务仅监听 `127.0.0.1`，没有云端后端，不上传键盘或聊天数据。仅保存生命周期元数据：会话与回合标识、时间、事件或工具名称、本地日志路径与读取位置。为补齐没有 `Stop` Hook 的任务结束，程序读取已接入的本地 Codex 日志中的生命周期记录，不保存聊天正文、工具参数或工具响应。

生成文件保存在被 Git 忽略的 **`runtime/`** 中：

- `preferences.json`：语言、颜色与灯效。迁移时可保留。
- `original-lighting.json`：接管期间的原灯光快照，恢复成功前请保留。
- 会话状态、设备回执、锁文件和进程日志：本地运行数据。

异常退出或拔线可能让键盘暂时保留上次灯效。手动恢复前，重新连接 USB、移除 Hook、停止 Web 服务，并等灯光进程退出。若自定义了空闲灯效，请先把空闲重置为「键盘原灯效」，让进程可以退出。

```sh
# 仅移除当前项目的 Hook
.venv/bin/python bridge.py uninstall

# 灯光进程退出后，恢复捕获的原侧灯设置
.venv/bin/python nuphy.py restore
```

恢复前不要删除灯光快照。设置文件损坏时，页面会提示并提供重置入口，不会静默覆盖文件。

## 开发

保持 `npm start` 运行，在另一个终端运行 `npm run dev` 并打开 Vite 地址。执行 `npm run build` 后，刷新普通控制台即可加载新的前端。

```sh
npm test                             # 模拟协议、生命周期、设置、HTTP 与中英文目录测试
npm run build                        # 构建 React 前端
.venv/bin/python nuphy.py probe       # 读取设备信息，不改变灯光
.venv/bin/python bridge.py status     # 检查本地事件状态
```

CI 在 macOS 上运行测试与构建，无需连接键盘。测试覆盖协议拒绝、灯光恢复、多个页面测试竞争、设置持久化、过期编辑、本机 HTTP 访问与 Hook 安装。实物验证独立进行：已在 Air75 V3 ANSI 上验证 USB 配置回读、全部五种侧灯灯效与恢复，并确认按键背光保持不变。

`src/` 为 React 界面，`webapp.py` 为本地 API，`bridge.py` 为生命周期控制器，`preferences.py` 为共享配置校验，`nuphy.py` 为 HID 协议实现。

## 已知边界

- 已验证 USB 标识为 `19f5:1028`。实测的 `19f5:2620` 接收器拒绝灯光查询；尚未实现蓝牙和接收器控制。
- 原厂固件把两侧灯条视为一个区域，不能左右独立显示状态或逐颗显示进度。
- 灯效写入间隔至少两秒；长期频繁写入的存储耐久性尚未验证。
- 仅跟踪发出受支持生命周期事件的本地 Codex 会话，云端编排的 Work 聊天不在支持范围内。本版本使用默认的 `~/.codex` 路径。
- 缺少结束事件的会话最多保留 24 小时。绿灯表示本轮结束，不保证任务正确或测试通过。
- 页面键盘为示意图；设备回读确认的是配置，不能代替观察实物 LED。

## 致谢

- [OpenAI Hooks 文档](https://learn.chatgpt.com/docs/hooks)：生命周期事件与用户信任机制。
- [kbvu 协议研究](https://github.com/pda/kbvu/blob/main/docs/keyboard-protocol.md)、[N Agent Bridge 协议文档](https://github.com/bohu8264/N-Agent-Bridge/blob/main/docs/HID-PROTOCOL.md)：Air75 V3 协议参考。
- [cython-hidapi](https://github.com/trezor/cython-hidapi)：本地 HID 通信。
- 侧灯原厂灯效名称与编号已对照 NuPhy IO，并经设备回读验证。

采用 [MIT 许可证](LICENSE)。这是独立的社区项目，与 NuPhy 或 OpenAI 无隶属关系。
