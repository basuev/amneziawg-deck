import commonjs from "@rollup/plugin-commonjs";
import json from "@rollup/plugin-json";
import nodeResolve from "@rollup/plugin-node-resolve";
import replace from "@rollup/plugin-replace";
import typescript from "@rollup/plugin-typescript";
import importAssets from "rollup-plugin-import-assets";
import { readFileSync } from "fs";

const manifest = JSON.parse(readFileSync("./plugin.json", "utf-8"));

const deckyManifestPlugin = {
  name: "decky-manifest",
  resolveId(id) {
    if (id === "@decky/manifest") return "\0virtual:decky-manifest";
    return null;
  },
  load(id) {
    if (id === "\0virtual:decky-manifest") {
      return `export default ${JSON.stringify(manifest)};`;
    }
    return null;
  },
};

const REACT_HOOK_NAMES = [
  "useState", "useEffect", "useCallback", "useRef", "useMemo",
  "useContext", "useReducer", "useLayoutEffect", "useImperativeHandle",
  "useDebugValue", "useId", "useTransition", "useDeferredValue",
  "useSyncExternalStore", "useInsertionEffect",
  "Fragment", "createElement", "cloneElement", "Children",
  "Component", "PureComponent", "isValidElement",
  "Suspense", "lazy", "memo", "forwardRef", "createContext",
];

const DECKY_UI_NAMES = [
  "definePlugin", "staticClasses",
  "PanelSection", "PanelSectionRow",
  "ToggleField", "Field", "ButtonItem",
  "showModal", "ConfirmModal", "ModalRoot",
];

const globalShimPlugin = {
  name: "global-shim",
  resolveId(id) {
    if (id === "react") return "\0virtual:react";
    if (id === "react-dom") return "\0virtual:react-dom";
    if (id === "@decky/ui") return "\0virtual:decky-ui";
    return null;
  },
  load(id) {
    if (id === "\0virtual:react") {
      const exports = REACT_HOOK_NAMES.map((n) => `export const ${n} = R.${n};`).join("\n");
      return `const R = window.SP_REACT;\nexport default R;\n${exports}`;
    }
    if (id === "\0virtual:react-dom") {
      return `const RD = window.SP_REACTDOM;\nexport default RD;\nexport const { render, createPortal, flushSync, findDOMNode, unmountComponentAtNode } = RD;`;
    }
    if (id === "\0virtual:decky-ui") {
      const exports = DECKY_UI_NAMES.map((n) => `export const ${n} = D.${n};`).join("\n");
      return `const D = window.DFL;\nif (!D) { throw new Error("[@decky/ui shim] window.DFL is not available"); }\nexport default D;\n${exports}`;
    }
    return null;
  },
};

export default {
  input: "./src/index.tsx",
  context: "window",
  external: [],
  output: {
    file: "dist/index.js",
    format: "esm",
  },
  plugins: [
    deckyManifestPlugin,
    globalShimPlugin,
    replace({
      preventAssignment: true,
      "process.env.NODE_ENV": JSON.stringify("production"),
      __PLUGIN_NAME__: JSON.stringify(manifest.name),
    }),
    commonjs(),
    nodeResolve({ browser: true }),
    typescript({ tsconfig: "./tsconfig.json", noEmit: false }),
    json(),
    importAssets({
      publicPath: `http://127.0.0.1:1337/plugins/${manifest.name}/`,
    }),
  ],
};
