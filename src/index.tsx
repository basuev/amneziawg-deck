import * as React from "react";
import { definePlugin, staticClasses } from "@decky/ui";
import { FaShieldAlt } from "react-icons/fa";

import { ConnectionToggle } from "./components/ConnectionToggle";
import { StatusPanel } from "./components/StatusPanel";
import { ConfigPanel } from "./components/ConfigPanel";
import { LogsPanel } from "./components/LogsModal";
import { useStatus } from "./hooks/useStatus";

function Content() {
  const { status, configs, configsDir, update, refresh } = useStatus();
  return (
    <>
      <ConnectionToggle
        status={status}
        configsCount={configs.length}
        onChanged={refresh}
      />
      <StatusPanel status={status} />
      <ConfigPanel configs={configs} configsDir={configsDir} />
      <LogsPanel update={update} />
    </>
  );
}

export default definePlugin(() => ({
  name: "AmneziaWG",
  titleView: <div className={staticClasses.Title}>AmneziaWG</div>,
  content: <Content />,
  icon: <FaShieldAlt />,
}));
