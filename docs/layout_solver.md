# Factory Layout Solver: ILP Formulation

This is based on the [Cook-Levin Theorem](https://en.wikipedia.org/wiki/Cook%E2%80%93Levin_theorem).
Inspired by having as many variables and constraints as you desire.

I'm hoping [HiGHS](https://highs.dev/) will find a solution to the ILP form.
If not, [z3](https://github.com/Z3Prover/z3) (as SMT) might work
(finds solution but maybe too slow).

This form includes only conveyors (no pipes),
but should be generalizable to pipes without much issues.
Pipes are identical to conveyors and can overlap with each other.
Treat pipe splitters, mergers, bridges as a facility
(so they cannot overlap conveyors).

Liquid usage can be optimized by quantizing liquids to multiples of 0.5/s.
More generally, you can use quantization for fractional usage of any material.

Depot unloader needing to be next to the depot bus can be generalized as
"powered regions" with radius 1.

Depot bus sections being connected to the depot bus port can be generalized as
"powered regions". There is a ordering applied to depot bus sections
such as lower tier bus sections must be connected to either
a strictly higher tier bus or the depot bus port itself.

### Definitions

- **anchor**: a facility's anchor cell is the cell used to represent
  the existence of the facility. It can be top-left occupied cell of the facility.
- **theoretically**: assumes the facility is powered and at maximum production
  (i.e. theoretical usage in-game).

### Notation

- $C$ is the set of cells.
  - $c\in C$ is some cell.
- $D=\{\texttt{U}, \texttt{R}, \texttt{D}, \texttt{L} \}$ is the set of directions.
  - $d\in D$ is some direction.
  - $D_p=\{\{\texttt{U}, \texttt{D}\}, \{\texttt{L}, \texttt{R}\}\}$
    is the set of directions pairs (along same axis).
- $I$ is the set of items.
  - $i\in I$ is some item.
- $F$ is the set of facilities.
  - $f\in F$ is some facility.
    Note that facilities in the model have fixed orientation.
    Each facility has 4 rotation variants.
  - $F_r\subseteq F$ is the subset of facilities that **require** power.
  - $F_p\subseteq F$ is the subset of facilities that **provide** power (i.e. electric pylon).
- $\rho_{fc}$ is the region occupied by facility $f$, $f$ is anchored to cell $c$.
- $\pi_{fc}$ is the the region **powered** by facility $f$,
  $f$ is anchored to cell $c$.
- $\bigwedge_x^X$ represents $\forall x\in X$.
  The big form of $\forall$ is kinda buggy in Katex.
- $\alpha_{fi} \in\Z^+_0$ represents the number of belts worth of item $i$
  that facility $f$ theoretically consumes.
- $\beta_{fi} \in\Z^+_0$ represents the number of belts worth of item $i$
  that facility $f$ theoretically produces.
- $\sigma^i_{fc} \ni (c',d')$ is the set of oriented cells that are
  the **input** ports of a facility $f$ anchored at cell $c$.
- $\sigma^o_{fc} \ni (c',d')$ is the set of oriented cells that are
  the **output** ports of a facility $f$ anchored at cell $c$.
- $\iota_{cd} \ni (c',d')$ is the set of oriented cells that can
  flow into cell $c$ in direction $d$. Note that $d,d'$ are never opposite
  directions, that is $(d,d')\notin D_p$.

### Variables

- $x_{cdi}\in\{0,1\}$ represents a variable for cell $c$ in direction $d$ is
  outputting item $i$ (implying a conveyor, or facility I/O port).
- $x_{fc}\in\{0,1\}$ represents a variable that a facility $f$ exists that is
  anchored to cell $c$.

## Constraints

Since HiGHS uses upper bounds only, all constraints are formulated as upper bounds.

### Item Flows

$$
\begin{align}
\bigwedge_c^C \bigwedge_d^D \sum_i^I x_{cdi} &\le 1 \\
\bigwedge_c^C \sum_d^D \sum_i^I x_{cdi} &\le 2 \\
\bigwedge_c^C \bigwedge_{\bf d}^{D_p} \sum_d^{\bf d} \sum_i^I x_{cdi} &\le 1 \\
\bigwedge_c^C \bigwedge_i^I \sum_d^D  \left[ x_{cdi} - \sum_{c'}^C \sum_{d':(c',d') \in \iota_{cd}}^D x_{c'd'i} - \sum_f^F \sum_{c':(c,d)\in \sigma^o_{fc'}}^C x_{fc'} \right] &\le 0 \\
\end{align}
$$

- $(1)$ At most one item type per flowing direction in a cell.
- $(2)$ Conveyor bridge can have at most 2 different directions flowing,
  but $(3)$ flow cannot be in opposite directions.
- $(4)$ All conveyors have a source of items;
  either the output of another conveyor or the output of a facility.

### Facility Restrictions

$$
\begin{align}
\bigwedge_c^C \left[ 4\left( \sum_f^F\sum_{c':c\in\rho_{fc'}}^C x_{fc'} \right) + \sum_d^D \sum_i^I x_{cdi} \right] &\le 4 \\
\bigwedge_c^C \bigwedge_f^{F_r} \left[ x_{fc} - \sum_{f'}^{F_p} \sum_{c':c'\in\rho_{fc}}^C \sum_{c'':c'\in\pi_{f'c''}}^C x_{f'c''} \right] &\le 0 \\
\bigwedge_c^C \bigwedge_i^I \bigwedge_f^F \left( \alpha_{fi} x_{fc} - \sum_d^D\sum_{c':(c',d)\in\sigma^i_{fc}}^C x_{c'di} \right) &\le 0 \\
\bigwedge_f^F \bigwedge_c^C \bigwedge_i^I \left[ \sum_{c'\in\sigma^o_{fc}}^C x_{c'di} - \sum_{c'}^{C} \min\left(\beta_{fi}, \left| \sigma^o_{fc} \cap \sigma^o_{fc'} \right| \right) \cdot x_{fc'} \right] &\le 0
% something about all overlaps... ??
\end{align}
$$

- $(5)$ At every grid square, either there is a facility or conveyor (not both).
- $(6)$ Every facilities' power needs are met.
  Any square of a facility that requires power is
  in the service region of a facility that provides power.
- $(7)$ A facility's input requirements are met.
- $(8)$ A facility's output capabilities are not exceeded.

### Layout Goals

$$
\begin{align}
-\sum_c^C x_{fc} \le -k
\end{align}
$$

$(9)$ There are at least $k$ instances of facility $f$ at maximum output.

$$
\begin{align}
\sum_c^C x_{fc} \le k
\end{align}
$$

$(10)$ There are no more than $k$ instances of a facility $f$.

## Minimization Criteria

The weights for all variables is $1$, less belts and less facilities are better.
