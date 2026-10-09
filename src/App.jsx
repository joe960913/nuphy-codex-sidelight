import React, { useEffect } from "react";
import { Badge, Diagnostic, Icon, Keyboard } from "./components";
import { STATE_IDS, STATE_ICONS, translator } from "./i18n";
import { usePanel } from "./usePanel";
import SettingsEditor from "./SettingsEditor";

export default function App() {
  const { snapshot: s, online, pending, notice, act } = usePanel();
  const language = s?.settings?.language || "zh-CN";
  const t = translator(language);
  const connected = Boolean(online && s?.connection.verified);
  const active = Boolean(s?.test.active);
  const owner = Boolean(s?.test.owner);
  const state = connected && s?.light.verified ? s.light.state : "unavailable";
  const profile = s?.light.profile || { color: "#89918E", effect: "system" };
  const previewColor =
    state === "unavailable" || profile.effect === "system"
      ? "#89918E"
      : profile.effect === "neon"
        ? "#a06fd3"
        : profile.color;
  const env = s?.environment;
  const keyboard = env?.keyboard;
  const codex = env?.codex;
  const loading = !s && online;
  const checked = s?.connection.checked_at
    ? new Date(s.connection.checked_at * 1000).toLocaleTimeString(language, {
        hour12: false,
      })
    : "—";
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = translator(language)("title");
  }, [language]);
  return (
    <div className="app-shell">
      <header className="header">
        <a className="brand" href="/" aria-label={t("home")}>
          <span className="brand-mark">
            <i />
            <i />
          </span>
          <span className="brand-name">NuPhy Codex Sidelight</span>
        </a>
        <div className="header-tools">
          <label className="language-control">
            <span className="sr-only">{t("language")}</span>
            <select
              value={language}
              disabled={!s || Boolean(pending) || !online}
              onChange={(event) =>
                act("settings", { language: event.target.value })
              }
            >
              <option value="zh-CN">中文</option>
              <option value="en">English</option>
            </select>
          </label>
          <span className={`local-status ${online ? "" : "offline"}`}>
            <i />
            {t(online ? "local" : "offline")}
          </span>
        </div>
      </header>
      <main>
        <section className="intro">
          <div>
            <span className="eyebrow">{t("eyebrow")}</span>
            <h1>
              {t("headline")}
              <span>{language === "en" ? "." : "。"}</span>
            </h1>
            <p>{t("intro")}</p>
          </div>
          <span className="device-label">
            <Icon name="keyboard" size={24} />
            <span>
              NuPhy Air75 V3<small>{t("usb_sync")}</small>
            </span>
          </span>
        </section>
        <section
          className="connection-section"
          aria-labelledby="connection-title"
        >
          <div className="section-heading">
            <h2 id="connection-title">
              <span className="section-index">01</span>
              {t("connection")}
            </h2>
            <button
              className="button secondary compact"
              onClick={() => act("probe")}
              disabled={Boolean(pending)}
            >
              <Icon
                name="refresh"
                size={15}
                className={pending === "probe" ? "spinning" : ""}
              />
              {t(pending === "probe" ? "probing" : "probe")}
            </button>
          </div>
          <div className="diagnostics">
            <Diagnostic
              icon="monitor"
              label={t("os")}
              loading={loading}
              ok={env?.mac && online}
              value={
                !online
                  ? t("unavailable_check")
                  : !env
                    ? t("checking")
                    : env.mac
                      ? "macOS"
                      : t("mac_required")
              }
              detail={
                env?.mac
                  ? `macOS ${env.os_version} · ${t("supported")}`
                  : t("check_host")
              }
            />
            <Diagnostic
              icon="spark"
              label="Codex"
              loading={loading}
              ok={codex?.installed && online}
              warning={codex && !codex.installed}
              value={
                !online
                  ? t("unavailable_check")
                  : !codex
                    ? t("checking")
                    : t(
                        codex.running
                          ? "running"
                          : codex.installed
                            ? "installed"
                            : "not_found",
                      )
              }
              detail={
                codex
                  ? `${t("hooks", { count: codex.hook_count })}${s.codex.sessions ? ` · ${t("events_received")}` : ""}`
                  : t("check_codex")
              }
            />
            <Diagnostic
              icon="keyboard"
              label={t("device")}
              loading={loading}
              ok={keyboard?.wired_count === 1 && online}
              warning={keyboard && keyboard.wired_count !== 1}
              value={
                !online
                  ? t("unavailable_check")
                  : !keyboard
                    ? t("checking")
                    : keyboard.wired_count === 1
                      ? "Air75 V3"
                      : t(
                          keyboard.wired_count > 1
                            ? "multiple"
                            : keyboard.receiver
                              ? "receiver"
                              : "no_keyboard",
                        )
              }
              detail={t(
                keyboard?.wired_count === 1
                  ? "interface_found"
                  : keyboard?.receiver
                    ? "receiver_hint"
                    : "plug_usb",
              )}
            />
            <Diagnostic
              icon="usb"
              label={t("wired")}
              loading={pending === "probe"}
              ok={connected}
              warning={!connected && Boolean(s)}
              value={t(
                pending === "probe"
                  ? "probing_device"
                  : connected
                    ? "usb_connected"
                    : "not_connected",
              )}
              detail={t(connected ? "readback_ok" : "wired_hint")}
            />
          </div>
        </section>
        <div className="workspace">
          <section
            className="preview-panel"
            aria-labelledby="preview-title"
            style={{ "--state-color": previewColor }}
          >
            <div className="preview-heading">
              <h2 id="preview-title">
                <span className="section-index">02</span>
                {t("preview")}
              </h2>
              <Badge
                tone={active ? "amber" : connected ? "green" : "neutral"}
                dot
              >
                {t(active ? "test_mode" : "auto_mode")}
              </Badge>
            </div>
            <div className="current-state">
              <span
                className={`state-glyph ${profile.effect === "breathe" && state !== "unavailable" ? "breathing" : ""}`}
              >
                <Icon name={STATE_ICONS[state]} size={23} />
              </span>
              <h3>{t(state)}</h3>
              <p>
                {active && state !== "unavailable"
                  ? t("simulated", { state: t(state) })
                  : t(`desc_${state}`)}
              </p>
            </div>
            <Keyboard
              state={state}
              profile={state === "unavailable" ? { effect: "system" } : profile}
            />
            <div className="light-caption">
              <span className="state-dot" />
              {state === "unavailable"
                ? t("no_light")
                : t(`effect_${profile.effect}`)}
              <span className="caption-divider" />
              {t("schematic")}
            </div>
            <div className="preview-bottom">
              <span>
                <Icon name="shield" size={14} />
                {t(connected ? "device_responded" : "waiting_device")}
              </span>
              <span>{t("last_check", { time: checked })}</span>
            </div>
          </section>
          <section className="test-panel" aria-labelledby="test-title">
            <div className="test-heading">
              <span className="eyebrow">{t("test_eyebrow")}</span>
              <h2 id="test-title">{t("test_title")}</h2>
              <p>
                {t(
                  active
                    ? owner
                      ? "test_choose"
                      : "test_other"
                    : "test_intro",
                )}
              </p>
            </div>
            <div className="state-options" aria-label={t("choose_state")}>
              {STATE_IDS.map((key, i) => {
                const selected = active && s?.test.state === key;
                const configured = s?.settings?.states[key];
                const confirmed =
                  selected &&
                  s?.light.mode === "test" &&
                  s?.light.applied_request_id === s?.test.request_id &&
                  s?.light.verified &&
                  s?.light.profile?.color === configured?.color &&
                  s?.light.profile?.effect === configured?.effect;
                return (
                  <button
                    key={key}
                    className={`state-option ${selected ? "selected" : ""}`}
                    style={{
                      "--option-color":
                        configured?.effect === "system"
                          ? "#89918E"
                          : configured?.color,
                    }}
                    aria-pressed={selected}
                    disabled={
                      !active || !owner || !connected || Boolean(pending)
                    }
                    onClick={() => act("test", { state: key })}
                  >
                    <span className="option-icon">
                      <Icon name={STATE_ICONS[key]} size={18} />
                    </span>
                    <span className="option-text">
                      <strong>{t(key)}</strong>
                      <small>
                        {configured ? t(`effect_${configured.effect}`) : "—"}
                      </small>
                    </span>
                    <span className="option-tail">
                      {pending === key ? (
                        <span className="spinner" />
                      ) : confirmed ? (
                        <Icon name="check" size={17} />
                      ) : (
                        <span>0{i + 1}</span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
            <button
              className={`button mode-button ${active ? "secondary" : "primary"}`}
              disabled={Boolean(pending) || (!active && !connected)}
              onClick={() =>
                active ? act("auto") : act("test", { state: "working" })
              }
            >
              {pending &&
              !["probe", "settings", "reset_settings"].includes(pending) ? (
                <>
                  <span className="spinner" />
                  {t("applying")}
                </>
              ) : (
                <>
                  {t(active ? "exit_test" : "enter_test")}
                  <Icon name="arrow" size={17} />
                </>
              )}
            </button>
            <p className="test-hint">
              {t(
                active
                  ? "close_hint"
                  : connected
                    ? "test_hint"
                    : "connect_first",
              )}
            </p>
          </section>
        </div>
        <div className="feedback" role="status" aria-live="polite">
          {!online ? (
            <div className="notice error">
              <Icon name="alert" size={17} />
              <span>{t("service_offline")}</span>
            </div>
          ) : notice ? (
            <div className={`notice ${notice.kind}`}>
              <Icon
                name={notice.kind === "error" ? "alert" : "check"}
                size={17}
              />
              <span>{t(notice.key)}</span>
            </div>
          ) : null}
        </div>
        <section className="follow-status" aria-label={t("live_status")}>
          <span className="follow-icon">
            <Icon name="spark" size={21} />
          </span>
          <div>
            <strong>{t("live_title")}</strong>
            <p>
              {!online
                ? t("wait_service")
                : s
                  ? `${t("live_detail", { state: t(s.codex.state), count: s.codex.sessions })} · ${t(active ? "after_test" : "sync_now")}`
                  : t("read_events")}
            </p>
          </div>
          <Badge tone={active ? "amber" : "neutral"}>
            {t(active ? "test_override" : "follow")}
          </Badge>
        </section>
        <SettingsEditor
          settings={s?.settings}
          error={s?.settings_error}
          t={t}
          act={act}
          pending={pending}
          online={online}
        />
      </main>
      <footer>
        <span>
          <Icon name="shield" size={14} />
          {t("private")}
        </span>
        <span>NUPHY CODEX SIDELIGHT / AIR75 V3</span>
      </footer>
    </div>
  );
}
