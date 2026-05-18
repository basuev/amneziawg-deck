import * as React from "react";
import { useState } from "react";
import { PanelSectionRow, ToggleField } from "@decky/ui";
import { connect, disconnect, Status } from "../api";

interface Props {
  status: Status;
  configsCount: number;
  onChanged: () => void;
}

function describe(status: Status, configsCount: number, busy: boolean): string {
  if (busy) return "Working";
  if (status.error) return `Error: ${status.error}`;
  if (configsCount === 0) return "No config found";
  return status.connected ? "Connected" : "Disconnected";
}

export function ConnectionToggle({ status, configsCount, onChanged }: Props) {
  const [busy, setBusy] = useState(false);
  const noConfig = configsCount === 0;

  return (
    <PanelSectionRow>
      <ToggleField
        label="AmneziaWG"
        description={describe(status, configsCount, busy)}
        checked={status.connected}
        disabled={busy || noConfig}
        onChange={async (next: boolean) => {
          setBusy(true);
          try {
            if (next) {
              await connect();
            } else {
              await disconnect();
            }
          } finally {
            setBusy(false);
            onChanged();
          }
        }}
      />
    </PanelSectionRow>
  );
}
