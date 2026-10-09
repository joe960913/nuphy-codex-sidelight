import { useEffect, useRef, useState } from "react";

const client = crypto.randomUUID();
let token;
export async function api(path, data, retry = true) {
  if (!token) {
    const response = await fetch("/api/bootstrap", {
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("service_offline");
    token = (await response.json()).token;
  }
  const response = await fetch(`/api/${path}`, {
    method: data === undefined ? "GET" : "POST",
    headers: {
      "X-Sidelight-Key": token,
      "X-Client-Id": client,
      ...(data !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: data === undefined ? undefined : JSON.stringify(data),
    signal: AbortSignal.timeout(6000),
  });
  if (response.status === 403 && retry) {
    token = null;
    return api(path, data, false);
  }
  const body = await response.json();
  if (!response.ok) throw new Error(body.code || "operation_failed");
  return body;
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function usePanel() {
  const [snapshot, setSnapshot] = useState(null);
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState("probe");
  const [notice, setNotice] = useState(null);
  const busy = useRef(false);
  const alive = useRef(true);
  const readSequence = useRef(0);
  async function refresh() {
    const sequence = ++readSequence.current;
    const next = await api("status");
    if (alive.current && sequence === readSequence.current) {
      setSnapshot(next);
      setOnline(true);
    }
    return next;
  }
  async function act(name, data = {}) {
    if (busy.current) return false;
    busy.current = true;
    setPending(name === "test" ? data.state : name);
    setNotice(null);
    try {
      const receipt = await api(name, data);
      if (name === "settings" || name === "reset_settings") {
        readSequence.current++;
        // A successful save is durable even if a subsequent status read fails.
        setSnapshot((previous) =>
          previous
            ? { ...previous, settings: receipt.settings, settings_error: null }
            : previous,
        );
        setNotice({
          kind: "success",
          key:
            name === "reset_settings"
              ? "settings_reset"
              : data.language
                ? "language_saved"
                : snapshot?.connection.verified
                  ? "settings_saved"
                  : "settings_saved_offline",
        });
        return receipt.settings;
      }
      const deadline = Date.now() + 12000;
      while (alive.current && Date.now() < deadline) {
        const next = await refresh();
        if (name === "probe" && next.connection.probe_id === receipt.probe_id) {
          if (!next.connection.verified) throw new Error("connect_failed");
          setNotice({ kind: "success", key: "probe_ok" });
          return true;
        }
        if (
          name !== "probe" &&
          next.light.applied_request_id === receipt.request_id &&
          next.light.verified &&
          next.light.mode === (name === "test" ? "test" : "auto")
        ) {
          setNotice({
            kind: "success",
            key: name === "test" ? "test_ok" : "auto_ok",
          });
          return true;
        }
        await delay(400);
      }
      throw new Error("confirmation_timeout");
    } catch (error) {
      if (error.message === "settings_conflict")
        await refresh().catch(() => {});
      if (alive.current)
        setNotice({
          kind: "error",
          key:
            error.name === "TimeoutError" || error instanceof TypeError
              ? "service_offline"
              : error.message,
        });
      return false;
    } finally {
      busy.current = false;
      if (alive.current) setPending(null);
    }
  }
  useEffect(() => {
    alive.current = true;
    act("probe");
    let fetching = false;
    const poll = setInterval(async () => {
      if (busy.current || fetching) return;
      fetching = true;
      try {
        await refresh();
      } catch {
        if (alive.current) setOnline(false);
      } finally {
        fetching = false;
      }
    }, 1500);
    const heartbeat = setInterval(
      () =>
        api("heartbeat", {}).catch(() => {
          if (alive.current) setOnline(false);
        }),
      5000,
    );
    return () => {
      alive.current = false;
      clearInterval(poll);
      clearInterval(heartbeat);
    };
  }, []);
  return { snapshot, online, pending, notice, act };
}
