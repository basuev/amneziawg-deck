import { callable } from "@decky/api";

export type Status = {
  connected: boolean;
  interface: string;
  public_endpoint: string;
  last_handshake_age: number | null;
  rx_bytes: number;
  tx_bytes: number;
  error: string | null;
};

export type Result = { ok: boolean; error?: string; note?: string };

export const DEFAULT_PLUGIN_DIR = "/home/deck/homebrew/plugins/AmneziaWG";
export const DEFAULT_CONFIGS_DIR = "/home/deck/homebrew/settings/AmneziaWG/configs";

export const EMPTY_STATUS: Status = {
  connected: false,
  interface: "wg0",
  public_endpoint: "",
  last_handshake_age: null,
  rx_bytes: 0,
  tx_bytes: 0,
  error: null,
};

export type UpdateInfo = {
  current: string;
  latest: string | null;
  url: string | null;
  newer: boolean;
  last_check_ts?: number;
};

export const EMPTY_UPDATE: UpdateInfo = {
  current: "",
  latest: null,
  url: null,
  newer: false,
};

export const connect = callable<[], Result>("connect");
export const disconnect = callable<[], Result>("disconnect");
export const getStatus = callable<[], Status>("get_status");
export const listConfigs = callable<[], string[]>("list_configs");
export const getLogs = callable<[number], string>("get_logs");
export const getPluginDir = callable<[], string>("get_plugin_dir");
export const getConfigsDir = callable<[], string>("get_configs_dir");
export const getUpdateInfo = callable<[], UpdateInfo>("get_update_info");
export const checkUpdateNow = callable<[], UpdateInfo>("check_update_now");
