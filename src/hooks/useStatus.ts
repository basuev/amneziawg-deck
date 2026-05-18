import { useCallback, useEffect, useState } from "react";
import { addEventListener, removeEventListener } from "@decky/api";
import {
  EMPTY_STATUS,
  EMPTY_UPDATE,
  Status,
  UpdateInfo,
  getStatus,
  listConfigs,
  getConfigsDir,
  getUpdateInfo,
} from "../api";

export function useStatus() {
  const [status, setStatus] = useState<Status>(EMPTY_STATUS);
  const [configs, setConfigs] = useState<string[]>([]);
  const [configsDir, setConfigsDir] = useState<string>("");
  const [update, setUpdate] = useState<UpdateInfo>(EMPTY_UPDATE);

  const refresh = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([getStatus(), listConfigs()]);
      setStatus(s);
      setConfigs(c);
    } catch {
      /* backend not ready yet */
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    getConfigsDir()
      .then((d) => mounted && setConfigsDir(d))
      .catch(() => {});
    getUpdateInfo()
      .then((u) => mounted && setUpdate(u))
      .catch(() => {});

    const statusHandler = (s: Status) => {
      if (mounted) setStatus(s);
    };
    const updateHandler = (u: UpdateInfo) => {
      if (mounted) setUpdate(u);
    };
    addEventListener<[Status]>("status_update", statusHandler);
    addEventListener<[UpdateInfo]>("update_available", updateHandler);

    refresh();

    return () => {
      mounted = false;
      removeEventListener<[Status]>("status_update", statusHandler);
      removeEventListener<[UpdateInfo]>("update_available", updateHandler);
    };
  }, [refresh]);

  return { status, configs, configsDir, update, refresh };
}
