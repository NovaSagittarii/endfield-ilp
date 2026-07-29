/**
 * https://vite.dev/guide/features#static-assets
 * https://github.com/lovasoa/highs-js#webassembly-loading
 */

import highsWasm from "../node_modules/highs/build/highs.wasm?url";
import loadHighs, { type HighsLinearSolutionColumn } from "highs";

import { type Facility, type Recipe } from "./items";
import { partition } from "./util";

const highs = await loadHighs({
  locateFile: (_: string) => highsWasm,
});

export interface RecipePlan {
  recipe: Recipe;
  used: number;
  allocated: number;
}

export interface RegionPlan {
  sell: Record<string, number>;
  power: RecipePlan[];
  powerGenerated: number;
  profit: number;
  recipes: RecipePlan[];
}

export function solve(
  F: Facility[],
  R: Recipe[],
  sell: Record<string, number>,
  itemLimit: Record<string, number>,
): RegionPlan {
  console.log(F);
  const items = [
    ...new Set(
      R.flatMap((r) => Object.keys(r.delta).concat(Object.keys(r.fixedDelta))),
    ),
  ];
  const sItems = Object.keys(sell);

  const itemFlow = Object.fromEntries(items.map((x) => [x, [] as string[]]));
  R.forEach((r, i) => {
    Object.entries(r.delta).forEach(([k, v]) =>
      itemFlow[k].push(`${v} use${i}`),
    );
    Object.entries(r.fixedDelta).forEach(([k, v]) =>
      itemFlow[k].push(`${v} alloc${i}`),
    );
  });
  sItems.forEach((item) =>
    itemFlow[item].push(`-1 sell${items.indexOf(item)}`),
  );

  const lpModel = `Maximize
 obj: ${Object.entries(sell)
   .map(([k, v]) => `${v} sell${items.indexOf(k)}`)
   .join(" + ")}
Subject To
${F.filter((f) => f.limit?.length)
  .map(
    (f) =>
      f.limit &&
      f.limit.length &&
      ` ${f.lname}_limit: ${f.recipes.map((r) => `alloc${R.indexOf(r)}`).join(" + ")} <= ${f.limit[f.limit.length - 1]}`,
  )
  .join("\n")}
${R.map(
  (r, i) =>
    r.limit && r.limit.length && `alloc${i} <= ${r.limit[r.limit.length - 1]}`,
)
  .filter((x) => x)
  .join("\n")}
${Object.entries(itemLimit)
  .map(
    // somehow all resource pumps/miners output at 20/m
    ([item, x]) =>
      ` ${item}_limit: ${itemFlow[item].filter((x) => x.startsWith("20")).join(" + ")} <= ${x}`,
  )
  .join("\n")}
${Object.entries(itemFlow)
  .map(
    ([item, x]) =>
      ` ${item}: ${x.join(" + ")} ${/power|_env$/.test(item) ? ">=" : "="} 0`,
  )
  .join("\n")}
${R.map((_, i) => ` use${i} - alloc${i} <= 0`).join("\n")}
General
${R.map((_, i) => ` alloc${i}`).join("\n")}
End`;
  console.log(lpModel);
  const result = highs.solve(lpModel, {
    mip_feasibility_tolerance: 1e-9,
    mip_rel_gap: 1e-7,
  });
  console.log(result);
  const cols = result.Columns as Record<string, HighsLinearSolutionColumn>;
  const [power, recipes] = partition(
    R.map((r, i) => ({
      recipe: r,
      used: cols[`use${i}`].Primal,
      allocated: cols[`alloc${i}`].Primal,
    })).filter(({ allocated }) => allocated >= 1e-8),
    (x) => x.recipe.fixedDelta["power"] > 0,
  );
  return {
    sell: Object.fromEntries(
      sItems
        .map((item) => [item, cols[`sell${items.indexOf(item)}`].Primal])
        .filter(([_k, v]) => v),
    ),
    profit: result.ObjectiveValue,
    power,
    recipes,
    powerGenerated: power.reduce(
      (acc, { recipe, allocated }) => acc + recipe.fixedDelta.power * allocated,
      0,
    ),
  };
}

export default highs;
