/**
 * https://vite.dev/guide/features#static-assets
 * https://github.com/lovasoa/highs-js#webassembly-loading
 */

import highsWasm from "../node_modules/highs/build/highs.wasm?url";
import loadHighs from "highs";

const highs = await loadHighs({
  locateFile: (_: string) => highsWasm,
});

export default highs;
