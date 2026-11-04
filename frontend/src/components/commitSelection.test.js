S// Vitest/Jest-style; adjust the import of `test`/`expect` to your runner.
import { defaultSelection } from "./commitSelection";
 
const mk = (n) => Array.from({ length: n }, (_, i) => ({ sha: String(i).padStart(40, "0") }));
 
test("single commit selected once", () => {
  expect(defaultSelection(mk(1))).toHaveLength(1);
});
 
test("<=10 selects all", () => {
  expect(defaultSelection(mk(10))).toHaveLength(10);
});
 
test("11-50 selects 10 distinct including first and last", () => {
  for (let n = 11; n <= 50; n++) {
    const c = mk(n);
    const sel = defaultSelection(c);
    expect(new Set(sel).size).toBe(10);
    expect(sel[0]).toBe(c[0].sha);
    expect(sel[9]).toBe(c[n - 1].sha);
  }
});
 
