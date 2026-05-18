import * as React from "react";
import { Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { Status } from "../api";
import { colors } from "../theme";

const STALE_HANDSHAKE_S = 180;
const UNITS = ["B", "KB", "MB", "GB", "TB"];

const fmtBytes = (n: number): string => {
  let value = n;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit++;
  }
  const precision = unit === 0 ? 0 : unit === 1 ? 1 : 2;
  return `${value.toFixed(precision)} ${UNITS[unit]}`;
};

const fmtAge = (s: number | null): string => {
  if (s === null) return "—";
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s ago`;
  return `${Math.floor(s / 3600)}h ago`;
};

const stateColor = (status: Status): string => {
  if (status.error) return colors.error;
  if (status.connected) return colors.ok;
  return colors.muted;
};

const handshakeColor = (age: number | null): string => {
  if (age === null) return colors.muted;
  if (age > STALE_HANDSHAKE_S) return colors.warn;
  return colors.ok;
};

export function StatusPanel({ status }: { status: Status }) {
  const stateLabel = status.error
    ? "Error"
    : status.connected
    ? "Connected"
    : "Disconnected";

  return (
    <PanelSection title="Status">
      <PanelSectionRow>
        <Field label="State" focusable={false}>
          <span style={{ color: stateColor(status) }}>{stateLabel}</span>
        </Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Endpoint" focusable={false}>
          {status.public_endpoint || "—"}
        </Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Handshake" focusable={false}>
          <span style={{ color: handshakeColor(status.last_handshake_age) }}>
            {fmtAge(status.last_handshake_age)}
          </span>
        </Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Received" focusable={false}>
          {fmtBytes(status.rx_bytes)}
        </Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Sent" focusable={false}>
          {fmtBytes(status.tx_bytes)}
        </Field>
      </PanelSectionRow>
    </PanelSection>
  );
}
