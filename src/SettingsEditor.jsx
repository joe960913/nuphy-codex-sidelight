import React, { useEffect, useState } from "react";
import { Icon } from "./components";
import { EFFECT_IDS, STATE_IDS, STATE_ICONS } from "./i18n";

function StateEditor({ state, profile, t, act, disabled }) {
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
            if (saved) setDraft(saved.states[state]);
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
          />
        ))}
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
