import { useEffect, useMemo, useState } from "react";
import { type RegionPlan, type RecipePlan } from "./solver";
import graphviz from "graphviz-wasm";

await graphviz.loadWASM();

function renderPowerRecipe({ recipe, allocated }: RecipePlan): string {
  const { power, ...rest } = Object.keys(recipe.fixedDelta).length
    ? recipe.fixedDelta
    : recipe.delta;
  console.assert(Object.values(rest).length === 1, { recipe, rest });
  const [item, rate] = Object.entries(rest)[0];
  return `${item} -> fuel [label="${allocated * -rate}(${allocated})"]`;
}

function renderRecipe(
  { recipe, used, allocated }: RecipePlan,
  id: number,
): string {
  const label =
    used + 1e-6 < allocated
      ? `${used.toFixed(2)}/${allocated}\n${recipe.facility.name}`
      : `${allocated}\n${recipe.facility.name}`;
  const { perMinute } = recipe;
  const { power: _, ...fixedCost } = recipe.fixedDelta;
  const lines = Object.entries(recipe.delta)
    .map(([item, rate]) => {
      if (rate < 0) {
        // input (cost)
        return `${item} -> r${id} [label=${(used * -rate).toFixed(2)},headlabel=${-rate / perMinute},labelcolor=gray,labelfontsize=8,labeldistance=1.5]`;
      } else {
        // output
        return `r${id} -> ${item} [label=${(used * rate).toFixed(2)},taillabel=${rate / perMinute},labelcolor=gray,labelfontsize=8,labeldistance=1.5]`;
      }
    })
    .concat(
      Object.entries(fixedCost).map(([item, rate]) => {
        if (rate < 0) {
          // input (cost)
          return `${item} -> r${id} [color=red, label="${allocated * -rate}",headlabel=${-rate},labelcolor=gray,labelfontsize=8,labeldistance=1.5]`;
        } else {
          // output
          return `r${id} -> ${item} [color=red, label="${allocated * rate}",taillabel=${rate},labelcolor=gray,labelfontsize=8,labeldistance=1.5]`;
        }
      }),
    );
  const xlabel = `xlabel=<<FONT COLOR='gray' POINT-SIZE='10'> ${recipe.seconds}s</FONT>>`;
  return (
    `r${id} [label="${label}", shape=note, color=red, margin=0, fontsize=10, ${xlabel}]\n` +
    lines.join("\n")
  );
}

function renderSellPlan([item, rate]: [string, number]): string {
  return `${item} -> sell [label="${rate.toFixed(2)}"]`;
}

function renderItem(item: string): string {
  if (item === "power") return ""; // suppress the dummy power item
  let attr = "color=black";
  let extra = "";
  if (item.endsWith("_ore")) {
    attr = `color=orange`;
    // extra = `ores -> ${item} [color=lightgray]`;
  } else if (item.endsWith("_env")) {
    attr = `shape=Mcircle, color=purple, margin=0, width=1, height=1, fixedsize=true`;
  }
  return `${item} [label="${item.replaceAll("_", " ")}", ${attr}]\n${extra}`;
}

function render(plan: RegionPlan): string {
  const items = [
    ...new Set(
      plan.recipes.flatMap((r) =>
        Object.keys(r.recipe.fixedDelta).concat(Object.keys(r.recipe.delta)),
      ),
    ),
  ];
  const dot = `
    digraph {
      # ores [label=ores, shape=Mdiamond, color=red, margin=0, width=0.3, height=0.3, fixedsize=true]
      sell [label="sell\n${(plan.profit * 60).toFixed(0)}/hr", shape=Msquare, color=green]
      fuel [label="fuel\n${plan.powerGenerated}W", shape=Msquare, color=brown]
      ${plan.power.map(renderPowerRecipe).join("\n")}
      ${Object.entries(plan.sell).map(renderSellPlan).join("\n")}
      ${items.map(renderItem).join("\n")}
      ${plan.recipes.map(renderRecipe).join("\n")}
    }
  `;
  return graphviz.layout(dot, "svg");
}

export function RegionPlan({ plan }: { plan: RegionPlan }) {
  const svg = useMemo(() => render(plan), [plan]);
  const [svgUrl, setSvgUrl] = useState("");
  useEffect(() => {
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    setSvgUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setSvgUrl("");
    };
  }, [svg]);
  return (
    <div>
      <a href={svgUrl} download={true}>
        download svg
      </a>
      <img src={svgUrl} />
      <div className="svg" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  );
}
