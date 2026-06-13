// node --test truth-recovery/test-truth-recovery.mjs
// Measured invariants for the metasprint-dta truth-recovery yardstick. Seeded.
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { generate, makeRng } from './dgp-dta.mjs';
import { runCell, runGrid, summarize } from './harness.mjs';

describe('DTA DGP', () => {
  it('is reproducible for a fixed seed', () => {
    const a = generate(0.85, 0.80, 8, 'het_mod', makeRng(7));
    const b = generate(0.85, 0.80, 8, 'het_mod', makeRng(7));
    assert.deepEqual(a.studies, b.studies);
  });
});

describe('Truth-recovery (measured)', () => {
  it('the primary REML Wald-t CI recovers true Se/Sp at/above nominal (conservative at tiny k)', () => {
    const grid = runGrid({ reps: 400 });
    const s = summarize(grid);
    assert.ok(s['primary (Wald-t)'].meanCovSe >= 0.94,
      `primary covSe ${s['primary (Wald-t)'].meanCovSe} below nominal`);
    // at k=4 the t_{k-2} crit makes it conservative (over-covers)
    const cell = runCell(0.85, 0.80, 4, 'het_mod', 500, makeRng(20260613));
    assert.ok(cell['primary (Wald-t)'].covSe > 0.96, `k=4 primary covSe ${cell['primary (Wald-t)'].covSe} not conservative`);
  });

  it('HONEST NEGATIVE: the profile-likelihood CI (computed but not primary) UNDER-covers true Se/Sp', () => {
    const grid = runGrid({ reps: 400 });
    const s = summarize(grid);
    assert.ok(s['profile-LL'].meanCovSe < 0.92,
      `profile-LL covSe ${s['profile-LL'].meanCovSe} not under-covering`);
    assert.ok(s['profile-LL'].meanCovSe < s['primary (Wald-t)'].meanCovSe - 0.05,
      `profile-LL ${s['profile-LL'].meanCovSe} not clearly below primary ${s['primary (Wald-t)'].meanCovSe}`);
  });

  it('genuine HKSJ does not improve here (the REML primary already covers/over-covers)', () => {
    const grid = runGrid({ reps: 400 });
    const s = summarize(grid);
    assert.ok(Math.abs(s['genuine-HKSJ'].meanCovSe - s['primary (Wald-t)'].meanCovSe) < 0.03,
      `HKSJ ${s['genuine-HKSJ'].meanCovSe} vs primary ${s['primary (Wald-t)'].meanCovSe} -- unexpectedly different`);
  });
});
