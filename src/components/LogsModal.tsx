import * as React from "react";
import { useEffect, useState } from "react";
import {
  ButtonItem,
  ConfirmModal,
  Field,
  PanelSection,
  PanelSectionRow,
  showModal,
} from "@decky/ui";
import { UpdateInfo, getLogs } from "../api";
import { colors, fontSize } from "../theme";

const LOG_TAIL_LINES = 300;

function LogsModalInner({ closeModal }: { closeModal?: () => void }) {
  const [text, setText] = useState<string>("Loading");

  useEffect(() => {
    getLogs(LOG_TAIL_LINES)
      .then((t) => setText(t || "(empty)"))
      .catch((e) => setText(`Error: ${String(e)}`));
  }, []);

  return (
    <ConfirmModal
      strTitle={`Logs (last ${LOG_TAIL_LINES} lines)`}
      strOKButtonText="Close"
      bAlertDialog
      onOK={closeModal}
    >
      <pre
        style={{
          fontSize: fontSize.mono,
          maxHeight: "60vh",
          overflow: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        {text}
      </pre>
    </ConfirmModal>
  );
}

function UpdateUrlModal({
  url,
  closeModal,
}: {
  url: string;
  closeModal?: () => void;
}) {
  return (
    <ConfirmModal
      strTitle="Update available"
      strOKButtonText="Close"
      bAlertDialog
      onOK={closeModal}
    >
      <div style={{ fontSize: fontSize.body, lineHeight: 1.4 }}>
        In Decky: <b>Settings → Developer → Install Plugin from URL</b>, paste:
        <div
          style={{
            fontSize: fontSize.mono,
            marginTop: 8,
            wordBreak: "break-all",
          }}
        >
          {url}
        </div>
      </div>
    </ConfirmModal>
  );
}

export function LogsPanel({ update }: { update: UpdateInfo }) {
  return (
    <PanelSection title="Diagnostics">
      <PanelSectionRow>
        <Field label="Version" focusable={false}>
          {update.current || "—"}
        </Field>
      </PanelSectionRow>
      {update.newer && update.url && (
        <>
          <PanelSectionRow>
            <Field label="Update" focusable={false}>
              <span style={{ color: colors.warn }}>{update.latest} available</span>
            </Field>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() =>
                showModal(<UpdateUrlModal url={update.url as string} />)
              }
            >
              Show Update URL
            </ButtonItem>
          </PanelSectionRow>
        </>
      )}
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={() => showModal(<LogsModalInner />)}
        >
          View Logs
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
