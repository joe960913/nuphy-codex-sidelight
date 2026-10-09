import React from "react";

export function Icon({ name, size = 20, ...props }) {
  const paths = {
    check: <path d="m5 12 4 4L19 6" />,
    refresh: (
      <>
        <path d="M20 7v5h-5M4 17v-5h5" />
        <path d="M6.2 7A7 7 0 0 1 18 6l2 3M4 15l2 3a7 7 0 0 0 11.8-1" />
      </>
    ),
    monitor: (
      <>
        <rect x="3" y="3" width="18" height="13" rx="2" />
        <path d="M8 21h8m-4-5v5" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" />
        <path d="m20 2 .5 1.5L22 4l-1.5.5L20 6l-.5-1.5L18 4l1.5-.5Z" />
      </>
    ),
    keyboard: (
      <>
        <rect x="2" y="5" width="20" height="14" rx="3" />
        <path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 15h10" />
      </>
    ),
    usb: (
      <>
        <path d="M12 21V3m-3 3 3-3 3 3M12 16l-5-4V9m5 4 5-3V7" />
        <circle cx="7" cy="7" r="2" />
        <path d="M15 4h4v3h-4z" />
      </>
    ),
    pause: (
      <>
        <path d="M8 5v14M16 5v14" />
      </>
    ),
    alert: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v6m0 4h.01" />
      </>
    ),
    moon: <path d="M20.5 13A8.5 8.5 0 0 1 11 3.5 8.5 8.5 0 1 0 20.5 13Z" />,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    shield: (
      <>
        <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] || paths.spark}
    </svg>
  );
}

export function Badge({ children, tone = "neutral", dot = false }) {
  return (
    <span className={`badge ${tone}`}>
      {dot && <i />}
      {children}
    </span>
  );
}

export function Diagnostic({
  icon,
  label,
  value,
  detail,
  ok,
  loading,
  warning,
}) {
  return (
    <div className="diagnostic">
      <div className="diagnostic-top">
        <span className="diagnostic-icon">
          <Icon name={icon} size={18} />
        </span>
        <span>{label}</span>
        <span
          className={`check-circle ${loading ? "loading" : ok ? "ok" : warning ? "warn" : ""}`}
        >
          {loading ? (
            <span className="spinner" />
          ) : ok ? (
            <Icon name="check" size={12} />
          ) : (
            <span className="small-dot" />
          )}
        </span>
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

const KEY_ROWS = [
  [
    ["esc", 1, "accent"],
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "F10",
    "F11",
    "F12",
    "del",
  ],
  ["~", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "−", "=", ["⌫", 1.6]],
  [
    ["tab", 1.4],
    "Q",
    "W",
    "E",
    "R",
    "T",
    "Y",
    "U",
    "I",
    "O",
    "P",
    "[",
    "]",
    ["\\", 1.2],
  ],
  [
    ["caps", 1.65],
    "A",
    "S",
    "D",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    ";",
    "'",
    ["return", 1.9, "return"],
  ],
  [
    ["shift", 2.1],
    "Z",
    "X",
    "C",
    "V",
    "B",
    "N",
    "M",
    ",",
    ".",
    "/",
    ["shift", 1.2],
    "↑",
  ],
  [["ctrl", 1.1], "⌥", "⌘", [" ", 6.2], "⌘", "fn", "←", "↓", "→"],
];

export function Keyboard({ state, profile }) {
  return (
    <div
      className="keyboard-stage"
      data-state={state}
      data-effect={profile?.effect}
      style={{
        "--glow": profile?.effect === "system" ? "#c3c9bd" : profile?.color,
      }}
      aria-hidden="true"
    >
      <div className="cable" />
      <div className="keyboard">
        <div className="lightbar left">
          {Array.from({ length: 10 }, (_, i) => (
            <i key={i} style={{ "--led-index": i }} />
          ))}
        </div>
        <div className="keys">
          {KEY_ROWS.map((row, i) => (
            <div className={`key-row row-${i}`} key={i}>
              {row.map((key, j) => {
                const [label, width = 1, style = ""] = Array.isArray(key)
                  ? key
                  : [key];
                return (
                  <div
                    className={`key ${style}`}
                    style={{ flex: width }}
                    key={j}
                  >
                    {label}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="lightbar right">
          {Array.from({ length: 10 }, (_, i) => (
            <i key={i} style={{ "--led-index": i }} />
          ))}
        </div>
      </div>
      <span className="keyboard-caption">
        <span /> Air75 V3 <span />{" "}
      </span>
    </div>
  );
}
