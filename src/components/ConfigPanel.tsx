import * as React from "react";
import { Field, PanelSection, PanelSectionRow } from "@decky/ui";
import { DEFAULT_CONFIGS_DIR } from "../api";
import { colors, fontSize } from "../theme";

interface Props {
  configs: string[];
  configsDir: string;
}

export function ConfigPanel({ configs, configsDir }: Props) {
  const path = configsDir || DEFAULT_CONFIGS_DIR;

  if (configs.length === 0) {
    return (
      <PanelSection title="Setup">
        <PanelSectionRow>
          <Field label="1. Export" focusable={false}>
            Amnezia desktop → Share VPN → AmneziaWG native config
          </Field>
        </PanelSectionRow>
        <PanelSectionRow>
          <Field label="2. Copy to Deck" focusable={false}>
            <span style={{ fontSize: fontSize.mono, wordBreak: "break-all" }}>
              {`scp wg0.conf deck@<deck-ip>:${path}/`}
            </span>
          </Field>
        </PanelSectionRow>
        <PanelSectionRow>
          <Field label="3. Reopen" focusable={false}>
            Close and open this panel again
          </Field>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  return (
    <PanelSection title="Config">
      <PanelSectionRow>
        <Field label="Active" focusable={false}>
          {configs[0]}
        </Field>
      </PanelSectionRow>
      {configs.length > 1 && (
        <PanelSectionRow>
          <Field label="Note" focusable={false}>
            <span style={{ color: colors.warn }}>
              {configs.length} configs found, using the first
            </span>
          </Field>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
