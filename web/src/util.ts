export function partition<T>(
  arr: T[],
  predicate: (x: T) => boolean,
): [T[], T[]] {
  return arr.reduce(
    (acc, val) => {
      acc[predicate(val) ? 0 : 1].push(val);
      return acc;
    },
    [[] as T[], [] as T[]],
  );
}
