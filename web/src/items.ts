import itemsYaml from "./assets/items.yaml?raw";
import { parse as parseYaml } from "yaml";

/*
```yaml
raw_resources: str[]
facilities:
  - name: str
    power: int (power_usage)
    seconds: int=60 (default recipe time)
    feature: str="" (default feature flag)
    fixed?: (default fixed costs)
      power: int (power_delta)
      *: int (delta per interval)
      *: str (in form `{X}/m`)
    recipes:
      - seconds: int (override recipe time)
        fixed?: (override fixed costs)
        feature?: (override feature flag)
        *: int (delta per interval)
        *: str (in form `{X}/m`)
sell:
  {region}:
    *: int (value of item in region)
```
*/
namespace Items {
  type SellPrices = Record<string, number>;
  type Deltas = Record<string, number | string>;
  export interface Yaml {
    raw_resources: string[];
    facilities: Facility[];
    items: Record<string, any>;
    sell: Record<string, SellPrices>;
  }
  interface Facility {
    name: string;
    power?: number;
    seconds?: number;
    feature?: string;
    fixed?: Record<string, number | string>;
    recipes?: (Recipe & Deltas)[];
    limit?: number[];
  }
  interface Recipe {
    seconds?: number;
    fixed?: Deltas;
    feature?: string;
    limit?: number[];
  }
}

export interface Facility {
  name: string;
  lname: string;
  recipes: Recipe[];
  powerUsage: number;
  limit?: number[];
}

export interface Recipe {
  fixedDelta: Record<string, number>; // fixed costs
  delta: Record<string, number>; // variable costs
  feature: string;
  facility: Facility;
  limit?: number[];
  seconds: number;
  perMinute: number;
}

const data = parseYaml(itemsYaml) as Items.Yaml;

function calculateFlow(x: string | number, seconds: number) {
  if (typeof x === "number") return (x * 60) / seconds;
  else if (typeof x !== "string") throw new Error("Invalid type of" + x);
  else if (x.endsWith("/m")) return parseFloat(x);
  throw new Error("Cannot compute flow of " + arguments);
}

export const rawResources = data.raw_resources;

export const facilities = data.facilities.map((f) => {
  const recipes = (f.recipes || []).map((r) => {
    const {
      seconds = f.seconds ?? 60,
      feature = f.feature,
      fixed = f.fixed ?? {},
      limit = [],
      ...recipe
    } = r;
    const { power = -(f.power ?? 0), ...fixedDelta } = fixed;
    return {
      limit,
      fixedDelta: {
        ...({ power } as Record<string, number>),
        ...Object.fromEntries(
          Object.entries(fixedDelta).map(([k, v]) => [
            k,
            calculateFlow(v, seconds),
          ]),
        ),
      },
      delta: Object.fromEntries(
        Object.entries(recipe).map(([k, v]) => [k, calculateFlow(v, seconds)]),
      ),
      feature,
      seconds,
      perMinute: 60 / seconds,
    } as Recipe;
  });
  return {
    name: f.name,
    lname: f.name.replace(/\s/g, "_").toLowerCase(),
    recipes,
    powerUsage: f.power ?? -f.fixed?.power!,
    limit: f.limit ?? [],
  } as Facility;
});

export const recipes = facilities.flatMap((f) =>
  f.recipes.map((r) => {
    r.facility = f;
    return r;
  }),
);

export const featureFlags = new Set(recipes.map((r) => r.feature));
export const _data = data;
