export const STATE_IDS = ["working", "waiting", "complete", "error", "idle"];
export const EFFECT_IDS = [
  "breathe",
  "static",
  "flow",
  "neon",
  "rhythm",
  "system",
];
export const STATE_ICONS = {
  working: "spark",
  waiting: "pause",
  complete: "check",
  error: "alert",
  idle: "moon",
  unavailable: "usb",
};

// Keep every user-facing string in one bilingual catalog, including API errors.
export const messages = {
  title: ["NuPhy Codex Sidelight — 状态灯", "NuPhy Codex Sidelight"],
  home: ["NuPhy Codex Sidelight 首页", "NuPhy Codex Sidelight home"],
  language: ["界面语言", "Language"],
  local: ["本地控制台", "Local console"],
  offline: ["服务已断开", "Service offline"],
  eyebrow: ["一点光，让状态更清晰", "A LITTLE LIGHT. A CLEARER STATE."],
  headline: ["让状态，看得见", "See what’s happening"],
  intro: [
    "把 Codex 的每一步，交给键盘两侧的光。",
    "Let your keyboard lights follow every step in Codex.",
  ],
  usb_sync: ["USB · 两侧同步", "USB · Both sides in sync"],
  connection: ["连接检查", "Connection check"],
  probe: ["测试连接", "Test connection"],
  probing: ["检测中…", "Checking…"],
  os: ["操作系统", "Operating system"],
  unavailable_check: ["无法检测", "Unavailable"],
  checking: ["正在检测", "Checking"],
  mac_required: ["需要 Mac", "Mac required"],
  supported: ["已支持", "Supported"],
  check_host: [
    "检测运行控制台的电脑",
    "Checks the computer running this console",
  ],
  running: ["正在运行", "Running"],
  installed: ["已安装", "Installed"],
  not_found: ["未检测到", "Not detected"],
  hooks: ["{count}/7 项事件已配置", "{count}/7 events configured"],
  events_received: ["已收到状态", "Status received"],
  check_codex: ["检查应用与事件连接", "Checking the app and event connection"],
  device: ["键盘设备", "Keyboard"],
  multiple: ["发现多把键盘", "Multiple keyboards"],
  receiver: ["仅发现接收器", "Receiver only"],
  no_keyboard: ["未发现键盘", "No keyboard found"],
  interface_found: ["已识别键盘配置接口", "Keyboard interface detected"],
  receiver_hint: [
    "接收器不能确认键盘在线",
    "A receiver does not confirm a keyboard connection",
  ],
  plug_usb: ["请连接 USB 数据线", "Connect a USB data cable"],
  wired: ["有线通道", "Wired connection"],
  probing_device: ["正在实测", "Testing device"],
  usb_connected: ["USB 已连通", "USB connected"],
  not_connected: ["尚未连通", "Not connected"],
  readback_ok: ["灯光配置回读成功", "Lighting readback verified"],
  wired_hint: [
    "需要有线模式与设备响应",
    "Requires wired mode and a device response",
  ],
  preview: ["灯光现场", "Live lights"],
  test_mode: ["测试模式", "Test mode"],
  auto_mode: ["自动联动", "Automatic"],
  working: ["工作中", "Working"],
  waiting: ["等待处理", "Waiting"],
  complete: ["本轮结束", "Turn ended"],
  error: ["运行异常", "Error"],
  idle: ["空闲", "Idle"],
  unavailable: ["等待连接", "Waiting for connection"],
  desc_working: [
    "Codex 正在思考或执行任务。",
    "Codex is thinking or working on a task.",
  ],
  desc_waiting: [
    "Codex 正在等待批准或同步输入。",
    "Codex is waiting for approval or a synchronous reply.",
  ],
  desc_complete: [
    "本轮已经结束，自动模式下保留 {seconds} 秒。",
    "The turn has ended. Kept for {seconds} seconds in automatic mode.",
  ],
  desc_error: [
    "任务异常退出，自动模式下保留 {seconds} 秒。",
    "The task ended with an error. Kept for {seconds} seconds in automatic mode.",
  ],
  desc_idle: ["当前没有正在执行的任务。", "No task is currently running."],
  desc_unavailable: [
    "用 USB 数据线连接键盘，并切换到有线模式。",
    "Connect a USB data cable and switch the keyboard to wired mode.",
  ],
  simulated: [
    "正在模拟「{state}」，实际 Codex 状态见下方。",
    "Simulating {state}. The actual Codex status is shown below.",
  ],
  effect_breathe: ["呼吸", "Breathe"],
  effect_static: ["常亮", "Steady"],
  effect_flow: ["流水", "Flow"],
  effect_neon: ["霓虹", "Neon"],
  effect_rhythm: ["律动", "Rhythm"],
  effect_system: ["键盘原灯效", "Original keyboard effect"],
  no_light: ["尚未确认灯光", "Lighting not verified"],
  schematic: ["灯光示意 · 两侧同步", "Illustration · Both sides in sync"],
  device_responded: ["已收到设备响应", "Device responded"],
  waiting_device: ["等待设备响应", "Waiting for device"],
  last_check: ["最近检测 {time}", "Last checked {time}"],
  test_eyebrow: ["试试每一种信号", "TRY THE SIGNALS"],
  test_title: ["每一种状态，都试试看。", "Try every signal."],
  test_choose: [
    "点击状态，观察键盘两侧的变化。",
    "Choose a state and watch both light bars.",
  ],
  test_other: [
    "另一个页面正在控制灯光测试。",
    "Another page is controlling the test.",
  ],
  test_intro: [
    "进入测试模式，亲自看看每一种灯光。",
    "Enter test mode to see each light on your keyboard.",
  ],
  choose_state: ["选择灯光状态", "Choose a light state"],
  applying: ["正在确认灯光…", "Verifying lights…"],
  exit_test: ["退出测试，恢复联动", "Exit test and resume"],
  enter_test: ["进入测试模式", "Enter test mode"],
  close_hint: [
    "关闭页面后，约 20 秒自动恢复联动。",
    "Automatic control resumes about 20 seconds after closing this page.",
  ],
  test_hint: [
    "测试期间暂时接管灯光，退出后继续跟随 Codex。",
    "Testing temporarily controls the lights. Exit to follow Codex again.",
  ],
  connect_first: [
    "有线通道检测通过后，即可开始测试。",
    "Verify the wired connection to start testing.",
  ],
  live_status: ["实时联动状态", "Live Codex status"],
  live_title: [
    "Codex 的实时状态一直在这里",
    "The real Codex status stays in view",
  ],
  wait_service: ["等待本地服务恢复。", "Waiting for the local service."],
  live_detail: [
    "当前{state} · {count} 个已接入会话",
    "{state} · {count} connected session(s)",
  ],
  after_test: ["退出测试后应用到键盘", "Applied after exiting test mode"],
  sync_now: ["自动同步到键盘", "Automatically synced to the keyboard"],
  read_events: ["正在读取本地事件…", "Reading local events…"],
  test_override: ["暂由测试接管", "Test override"],
  follow: ["跟随 Codex", "Following Codex"],
  private: [
    "本地运行 · 灯光数据不离开这台电脑",
    "Runs locally · Lighting data stays on this computer",
  ],
  settings: ["状态灯设置", "State light settings"],
  reset_all: ["恢复全部默认", "Reset all defaults"],
  settings_intro: [
    "为每个状态选择颜色和灯效，保存后自动联动与测试都会使用它。",
    "Choose a color and effect for each state. Saved settings apply to automatic control and tests.",
  ],
  state_column: ["状态", "State"],
  color: ["颜色", "Color"],
  effect: ["灯效", "Effect"],
  actions: ["操作", "Actions"],
  duration_title: ["自动联动提示时长", "Automatic notification duration"],
  duration_hint: [
    "各自默认 5 秒，可设为 2–60 秒，从收到结束或异常事件开始计时。测试模式不受此时长限制。",
    "Each defaults to 5 seconds. Choose 2–60 seconds, counted from the end or error event. Test mode has no such time limit.",
  ],
  duration_for: ["{state}提示时长", "{state} duration"],
  save_duration_for: ["保存{state}提示时长", "Save {state} duration"],
  reset_duration_for: ["恢复{state}默认时长", "Reset {state} duration"],
  seconds_unit: ["秒", "seconds"],
  duration_saved: ["提示时长已保存，自动联动会使用新时长。", "Duration saved. Automatic tracking will use the new duration."],
  invalid_duration: ["请输入 2–60 之间的整数秒数。", "Enter a whole number of seconds from 2 to 60."],
  color_for: ["{state}颜色", "{state} color"],
  hex_for: ["{state}颜色 HEX", "{state} HEX color"],
  effect_for: ["{state}灯效", "{state} effect"],
  save_for: ["保存{state}设置", "Save {state} settings"],
  reset_for: ["恢复{state}默认设置", "Reset {state} defaults"],
  save: ["保存", "Save"],
  saving: ["保存中…", "Saving…"],
  reset: ["恢复默认", "Reset"],
  unsaved: ["未保存", "Unsaved"],
  saved_label: ["已保存", "Saved"],
  original_color: ["由键盘原设置决定", "Uses the original keyboard settings"],
  neon_color: ["霓虹自动变色", "Neon cycles colors automatically"],
  effect_note: [
    "流水是侧灯的流动效果；“波浪”属于按键背光。律动由键盘内置效果驱动。",
    "Flow is the moving sidelight effect; Wave belongs to the key backlight. Rhythm uses the keyboard’s built-in effect.",
  ],
  defaults_note: [
    "状态行的恢复默认会重置该状态的配色、灯效与提示时长；“键盘原灯效”会恢复接管前的侧灯设置。",
    "Reset in a state row restores its default color, effect, and duration. Original keyboard effect restores the sidelights captured before control began.",
  ],
  persist_note: [
    "颜色、灯效、提示时长和语言都保存在这台电脑，重启后仍然保留。",
    "Colors, effects, durations, and language are saved on this computer and survive restarts.",
  ],
  probe_ok: [
    "连接测试通过，已收到键盘的灯光回读。",
    "Connection passed. The keyboard lighting was read back successfully.",
  ],
  test_ok: [
    "灯效已通过键盘回读确认，请观察两侧灯条。",
    "Lighting verified by device readback. Check both light bars.",
  ],
  auto_ok: [
    "已退出测试，恢复跟随 Codex。",
    "Test mode ended. Following Codex again.",
  ],
  settings_saved: [
    "已保存。该状态会使用新的颜色和灯效。",
    "Saved. This state will use the new color and effect.",
  ],
  settings_saved_offline: [
    "已保存到本机，重新连接键盘后生效。",
    "Saved locally. Applies when the keyboard reconnects.",
  ],
  settings_reset: [
    "已恢复默认设置，并保存到本机。",
    "Default settings restored and saved locally.",
  ],
  language_saved: ["已保存语言偏好。", "Language preference saved."],
  service_offline: [
    "本地服务没有响应，请重新启动控制台后刷新。",
    "The local service is not responding. Restart it and refresh this page.",
  ],
  connect_failed: [
    "有线通道尚未连通，请检查数据线和键盘模式。",
    "The wired connection is not ready. Check the cable and keyboard mode.",
  ],
  confirmation_timeout: [
    "暂未收到键盘确认，请检查 USB 连接后重试。",
    "No keyboard confirmation received. Check the USB connection and try again.",
  ],
  invalid_request: ["请求格式不正确。", "Invalid request format."],
  refresh_page: [
    "页面已过期，请刷新后重试。",
    "This page has expired. Refresh and try again.",
  ],
  invalid_state: ["未知的灯光状态。", "Unknown light state."],
  connect_usb: [
    "请连接 USB 数据线，并先测试连接。",
    "Connect a USB data cable and test the connection first.",
  ],
  other_owner: [
    "另一个页面正在测试，请先退出测试模式。",
    "Another page is testing. Exit test mode first.",
  ],
  local_only: ["仅允许本机访问。", "Only local access is allowed."],
  cross_origin: ["不允许跨站请求。", "Cross-site requests are not allowed."],
  operation_failed: [
    "操作未完成，请刷新后重试。",
    "The operation failed. Refresh and try again.",
  ],
  invalid_color: [
    "请输入有效的六位颜色，例如 #0060FF。",
    "Enter a six-digit hex color, such as #0060FF.",
  ],
  invalid_effect: [
    "当前键盘不支持这个侧灯效果。",
    "This sidelight effect is not supported by the keyboard.",
  ],
  invalid_profile: [
    "灯光设置格式不正确，请刷新后重试。",
    "Invalid light settings. Refresh and try again.",
  ],
  invalid_language: ["请选择中文或 English。", "Choose Chinese or English."],
  settings_conflict: [
    "此设置已在其他页面更新，已加载最新值，请重新编辑。",
    "This setting changed in another page. The latest values are loaded; edit again.",
  ],
  settings_corrupt: [
    "无法读取已存设置。当前使用默认值；可点“恢复全部默认”修复。",
    "Saved settings could not be read. Defaults are active; use Reset all defaults to repair them.",
  ],
};

export function translator(language) {
  return (key, values = {}) => {
    const template =
      messages[key]?.[language === "en" ? 1 : 0] ??
      messages.operation_failed[language === "en" ? 1 : 0];
    return template.replace(/\{(\w+)\}/g, (_, name) =>
      String(values[name] ?? ""),
    );
  };
}
