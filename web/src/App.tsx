import { solve } from "./solver";
import { facilities, recipes, _data } from "./items";
import { RegionPlan } from "./render";
import { useMemo } from "react";

function App() {
  const w = useMemo(
    () =>
      solve(
        facilities,
        recipes.filter((x) => !x.feature),
        _data.sell["wuling"],
        {
          originium_ore: 540,
          amethyst_ore: 0,
          ferrium_ore: 120,
          cuprium_ore: 420,
        },
      ),
    [],
  );
  console.log(w);
  return (
    <div>
      <RegionPlan plan={w} />
    </div>
  );
}

export default App;
