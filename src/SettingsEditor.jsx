import React, { useEffect, useState } from "react";
import { Icon } from "./components";
import { EFFECT_IDS, STATE_IDS, STATE_ICONS } from "./i18n";

function DurationEditor({ state, seconds, t, act, disabled }) {
  const [draft, setDraft] = useState(String(seconds));
  useEffect(() => setDraft(String(seconds)), [seconds]);
  const value = Number(draft);
  const valid = /^\d+$/.test(draft) && Number.isInteger(value) && value >= 2 && value <= 60;
  const dirty = !valid || value !== seconds;
  async function save(duration) {
    const saved = await act("settings", { state, duration, expected_duration: seconds });
    if (saved) setDraft(String(saved.durations[state]));
  }
  return (
    <div className="duration-card">
      <div className="duration-heading">
        <label htmlFor={`duration-${state}`}>{t("duration_for", { state: t(state) })}</label>
        <small className={dirty ? "unsaved" : ""}>{t(dirty ? "unsaved" : "saved_label")}</small>
      </div>
      <div className="duration-controls">
        <div className="duration-input">
          <input
            id={`duration-${state}`}
            type="number"
            min={2}
            max={60}
            step={1}
            value={draft}
            aria-invalid={!valid}
            aria-describedby={valid ? "duration-hint" : `duration-error-${state}`}
            disabled={disabled}
            onChange={(event) => setDraft(event.target.value)}
          />
          <span>{t("seconds_unit")}</span>
        </div>
        <button
          className="button primary compact"
          disabled={disabled || !dirty || !valid}
          aria-label={t("save_duration_for", { state: t(state) })}
          onClick={() => save(value)}
        >{t("save")}</button>
        <button
          className="button secondary compact"
          disabled={disabled}
          aria-label={t("reset_duration_for", { state: t(state) })}
          onClick={() => save(5)}
        >{t("reset")}</button>
      </div>
      {!valid && <p className="field-error" id={`duration-error-${state}`}>{t("invalid_duration")}</p>}
    </div>
  );
}

function StateEditor({ state, profile, t, act, disabled, onReset }) {
  const [draft, setDraft] = useState(profile);
  useEffect(() => {
    setDraft(profile);
  }, [profile.color, profile.effect]);
  const valid = /^#[0-9a-fA-F]{6}$/.test(draft.color);
  const dirty =
    draft.color.toUpperCase() !== profile.color ||
    draft.effect !== profile.effect;
  const automaticColor = ["system", "neon"].includes(draft.effect);
  return (
    <div className="setting-row">
      <div className="setting-state">
        <span
          className="option-icon"
          style={{ "--option-color": valid ? draft.color : "#89918E" }}
        >
          <Icon name={STATE_ICONS[state]} size={18} />
        </span>
        <div>
          <strong>{t(state)}</strong>
          <small className={dirty ? "unsaved" : ""}>
            {t(dirty ? "unsaved" : "saved_label")}
          </small>
        </div>
      </div>
      <div className="color-field">
        <div className={`color-inputs ${automaticColor ? "inactive" : ""}`}>
          <input
            type="color"
            aria-label={t("color_for", { state: t(state) })}
            value={valid ? draft.color : profile.color}
            disabled={disabled || automaticColor}
            onChange={(event) =>
              setDraft({ ...draft, color: event.target.value.toUpperCase() })
            }
          />
          <input
            type="text"
            aria-label={t("hex_for", { state: t(state) })}
            aria-invalid={!valid}
            spellCheck="false"
            maxLength={7}
            value={draft.color}
            disabled={disabled || automaticColor}
            onChange={(event) =>
              setDraft({ ...draft, color: event.target.value })
            }
          />
        </div>
        {!valid && <small className="field-error">{t("invalid_color")}</small>}
        {automaticColor && (
          <small>
            {t(draft.effect === "neon" ? "neon_color" : "original_color")}
          </small>
        )}
      </div>
      <select
        value={draft.effect}
        aria-label={t("effect_for", { state: t(state) })}
        disabled={disabled}
        onChange={(event) => setDraft({ ...draft, effect: event.target.value })}
      >
        {EFFECT_IDS.map((effect) => (
          <option key={effect} value={effect}>
            {t(`effect_${effect}`)}
          </option>
        ))}
      </select>
      <div className="setting-actions">
        <button
          className="button primary compact"
          disabled={disabled || !dirty || !valid}
          aria-label={t("save_for", { state: t(state) })}
          onClick={() =>
            act("settings", { state, profile: draft, expected: profile })
          }
        >
          {t("save")}
        </button>
        <button
          className="button secondary compact"
          disabled={disabled}
          aria-label={t("reset_for", { state: t(state) })}
          onClick={async () => {
            const saved = await act("reset_settings", { state });
            if (saved) {
              setDraft(saved.states[state]);
              onReset();
            }
          }}
        >
          {t("reset")}
        </button>
      </div>
    </div>
  );
}

export default function SettingsEditor({
  settings,
  t,
  act,
  pending,
  online,
  error,
}) {
  const [resetEpoch, setResetEpoch] = useState(0);
  const [stateEpochs, setStateEpochs] = useState({});
  if (!settings) return null;
  return (
    <section className="settings-section" aria-labelledby="settings-title">
      <div className="section-heading">
        <h2 id="settings-title">
          <span className="section-index">03</span>
          {t("settings")}
        </h2>
        <button
          className="button secondary compact"
          disabled={Boolean(pending) || !online}
          onClick={async () => {
            if (await act("reset_settings"))
              setResetEpoch((value) => value + 1);
          }}
        >
          <Icon name="refresh" size={14} />
          {t("reset_all")}
        </button>
      </div>
      <p className="settings-intro">{t("settings_intro")}</p>
      {error && (
        <p className="notice error" role="alert">
          {t(error)}
        </p>
      )}
      <div className="settings-table">
        <div className="setting-columns" aria-hidden="true">
          <span>{t("state_column")}</span>
          <span>{t("color")}</span>
          <span>{t("effect")}</span>
          <span>{t("actions")}</span>
        </div>
        {STATE_IDS.map((state) => (
          <StateEditor
            key={`${state}-${resetEpoch}`}
            state={state}
            profile={settings.states[state]}
            t={t}
            act={act}
            disabled={!online || Boolean(pending)}
            onReset={() => setStateEpochs((values) => ({ ...values, [state]: (values[state] || 0) + 1 }))}
          />
        ))}
      </div>
      <div className="duration-section">
        <h3>{t("duration_title")}</h3>
        <p id="duration-hint">{t("duration_hint")}</p>
        <div className="duration-grid">
          {["complete", "error"].map((state) => (
            <DurationEditor
              key={`${state}-${resetEpoch}-${stateEpochs[state] || 0}`}
              state={state}
              seconds={settings.durations[state]}
              t={t}
              act={act}
              disabled={!online || Boolean(pending)}
            />
          ))}
        </div>
      </div>
      <div className="settings-notes">
        <p>{t("effect_note")}</p>
        <p>{t("defaults_note")}</p>
        <p>
          <Icon name="shield" size={13} />
          {t("persist_note")}
        </p>
      </div>
    </section>
  );
}
