"""SimPy rebuild of Seppanen (2005), "Operator-Paced Assembly Line Simulation", Proc. WSC, pp. 1343-1349.

Every input below cites the paper. Inputs the paper does not give are marked ASSUMED and are the only
calibration knobs (see calibrate.py). Time unit: seconds.

Line (Fig. 1): 4 cells in series, buffers 1 / 2 / 1 between them, unlimited supply before cell 1,
units leave after cell 4. A cell holds a finished unit until the next buffer (or cell) has space (blocking).
Operators: one pool of n operators who walk to the cell that requests them (closest free operator first,
otherwise first-come first-served; Section 3.4). Operators required per cell: 1 / 1 / 0 / 2.
"""
import random
from dataclasses import dataclass, field

import simpy

MIN = 60.0


@dataclass
class Params:
    operators: int = 3                                   # Fig. 16: 2, 3, 4
    cycle_s: tuple = (40.0, 30.0, 58.0, 30.0)            # Fig. 1
    ops_needed: tuple = (1, 1, 0, 2)                     # Fig. 1
    buffers: tuple = (1, 2, 1)                           # Fig. 1 / Section 2
    shift_min: float = 480.0                             # Fig. 9
    schedule: tuple = ((110, 10), (105, 15), (110, 10), (105, 15))  # (work, off) minutes, Fig. 9
    orders: tuple = (40, 50, 10, 20, 40, 10, 20)         # batch sizes of SKUs 1..7, repeated, Fig. 4
    # intermittent duties (Fig. 10 for cell 1; Fig. 1 shows which apply to cells 2-4)
    sku_change_min: float = 2.0; sku_change_cv: float = 0.05         # before assembly, on SKU change
    materials_every: int = 10; materials_min: float = 1.0; materials_cv: float = 0.10  # after assembly
    reject_p: float = 0.01; reject_min: float = 0.5; reject_cv: float = 0.15            # before assembly
    duties: tuple = ("SMR", "SMR", "S", "SMR")           # S = change SKU, M = get materials, R = reject (Fig. 1)
    # failures (Fig. 11): gamma up / repair times, minutes; one operator repairs
    up_mean_min: tuple = (294.0, 294.0, 285.0, 294.0); up_shape: float = 0.7
    repair_mean_min: tuple = (6.0, 6.0, 15.0, 6.0); repair_shape: float = 1.3
    # ASSUMED (not in the paper) - calibration knobs
    walk_s_per_cell: float = 1.0       # operator walking time between neighbouring cells (calibrated)
    cycle_cv: float = 0.0              # variability of the assembly time (normal) (calibrated)
    transit_s: float = 5.0             # minimum transit time through a buffer / into the next cell (calibrated)
    dispatch_rule: str = "downstream"  # ASSUMED: which waiting request a freed operator serves: downstream cell first (calibrated) | fifo | upstream | closest
    breaks_stop_cell3: bool = False    # Arena removes operators only; automatic cell 3 keeps running
    seed: int = 1


@dataclass
class Op:
    id: int
    loc: int
    busy: bool = False


@dataclass
class Stats:
    produced: int = 0
    moves: int = 0
    move_segments: int = 0
    op_busy_s: float = 0.0


class Line:
    def __init__(self, env, p: Params, rng: random.Random):
        self.env, self.p, self.rng, self.st = env, p, rng, Stats()
        self.ops = [Op(i, loc=0) for i in range(p.operators)]   # ASSUMED: all start at cell 1
        self.queue = []                                          # pending operator requests (cell, event)
        self.on_break = False
        self.buf = [simpy.Store(env, capacity=c) for c in p.buffers]
        self.failed = [False] * 4
        self.order_pos, self.left_in_batch = 0, p.orders[0]
        env.process(self.schedule())
        for c in range(4):
            env.process(self.cell(c))
            env.process(self.failures(c))

    # ---- random helpers ----------------------------------------------------------------------
    def normal(self, mean, cv):
        return max(0.0, self.rng.gauss(mean, cv * mean)) if cv > 0 else mean

    def gamma(self, mean, shape):
        return self.rng.gammavariate(shape, mean / shape)

    # ---- operator pool -----------------------------------------------------------------------
    def request(self, cell):
        ev = self.env.event()
        self.queue.append((cell, ev))
        self.dispatch()
        return ev

    def release(self, op):
        op.busy = False
        self.dispatch()

    def dispatch(self):
        if self.on_break:
            return
        while self.queue:
            free = [o for o in self.ops if not o.busy]
            if not free:
                return
            if self.p.dispatch_rule == "downstream":
                k = max(range(len(self.queue)), key=lambda i: (self.queue[i][0], -i))
                cell, ev = self.queue.pop(k)
                op = min(free, key=lambda o: (abs(o.loc - cell), o.id))
            elif self.p.dispatch_rule == "upstream":
                k = min(range(len(self.queue)), key=lambda i: (self.queue[i][0], i))
                cell, ev = self.queue.pop(k)
                op = min(free, key=lambda o: (abs(o.loc - cell), o.id))
            elif self.p.dispatch_rule == "closest" and len(free) == 1:
                op = free[0]
                k = min(range(len(self.queue)), key=lambda i: (abs(self.queue[i][0] - op.loc), i))
                cell, ev = self.queue.pop(k)
            else:
                cell, ev = self.queue.pop(0)
                op = min(free, key=lambda o: (abs(o.loc - cell), o.id))
            op.busy = True
            self.env.process(self.walk(op, cell, ev))

    def walk(self, op, cell, ev):
        if op.loc != cell:
            self.st.moves += 1
            self.st.move_segments += abs(op.loc - cell)
            yield self.env.timeout(self.p.walk_s_per_cell * abs(op.loc - cell))
            op.loc = cell
        ev.succeed(op)

    def acquire(self, cell, held, n):
        while len(held) < n:
            op = yield self.request(cell)
            held.append(op)

    def work(self, held, seconds):
        t0 = self.env.now
        yield self.env.timeout(seconds)
        self.st.op_busy_s += (self.env.now - t0) * len(held)

    # ---- shift schedule: operators unavailable during breaks (Section 3.5) ------------------
    def schedule(self):
        for work, off in self.p.schedule:
            yield self.env.timeout(work * MIN)
            self.on_break = True
            yield self.env.timeout(off * MIN)
            self.on_break = False
            self.dispatch()

    # ---- failures (Section 3.7): clock-time up periods; repair starts when the cell is between units
    def failures(self, c):
        p = self.p
        while True:
            yield self.env.timeout(self.gamma(p.up_mean_min[c] * MIN, p.up_shape))
            self.failed[c] = True
            while self.failed[c]:          # cell process repairs it, then clears the flag
                yield self.env.timeout(1.0)

    def repair_if_failed(self, c):
        if self.failed[c]:
            held = []
            yield from self.acquire(c, held, 1)
            yield from self.work(held, self.gamma(self.p.repair_mean_min[c] * MIN, self.p.repair_shape))
            for o in held:
                self.release(o)
            self.failed[c] = False

    def next_sku(self):
        sku = self.order_pos
        self.left_in_batch -= 1
        if self.left_in_batch == 0:
            self.order_pos = (self.order_pos + 1) % len(self.p.orders)
            self.left_in_batch = self.p.orders[self.order_pos]
        return sku

    # ---- one cell ------------------------------------------------------------------------------
    def cell(self, c):
        p, env = self.p, self.env
        last_sku, count = 0, 0                         # ASSUMED: line set up for SKU 1 at shift start
        while True:
            yield from self.repair_if_failed(c)
            if c == 0:
                sku = self.next_sku()                  # unlimited supply of units
            else:
                sku, ready = yield self.buf[c - 1].get()
                if ready > env.now:
                    yield env.timeout(ready - env.now)
            held = []
            duties = p.duties[c]
            if "S" in duties and sku != last_sku:
                yield from self.acquire(c, held, 1)
                yield from self.work(held, self.normal(p.sku_change_min * MIN, p.sku_change_cv))
            last_sku = sku
            if "R" in duties and self.rng.random() < p.reject_p:
                yield from self.acquire(c, held, 1)
                yield from self.work(held, self.normal(p.reject_min * MIN, p.reject_cv))
            need = p.ops_needed[c]
            if need == 0:                               # automatic cell: release any duty operator
                for o in held:
                    self.release(o)
                held = []
                if p.breaks_stop_cell3:
                    while self.on_break:
                        yield env.timeout(1.0)
            yield from self.acquire(c, held, need)
            yield from self.work(held, self.normal(p.cycle_s[c], p.cycle_cv))
            count += 1
            if "M" in duties and count % p.materials_every == 0 and held:
                keep = held.pop(0)                      # this operator stocks material; cell carries on
                env.process(self.after_duty(keep, self.normal(p.materials_min * MIN, p.materials_cv)))
            for o in held:
                self.release(o)
            if c < 3:
                yield self.buf[c].put((sku, env.now + p.transit_s))
            else:
                self.st.produced += 1

    def after_duty(self, op, seconds):
        yield from self.work([op], seconds)
        self.release(op)


def run_once(p: Params, seed: int) -> dict:
    rng = random.Random(seed)
    env = simpy.Environment()
    line = Line(env, p, rng)
    env.run(until=p.shift_min * MIN)
    s = line.st
    return {
        "units_per_shift": s.produced,
        "operator_moves": s.moves,
        "operator_move_segments": s.move_segments,
        "units_per_operator": s.produced / p.operators,
        "cycle_time_s": p.shift_min * MIN / s.produced if s.produced else float("nan"),
        "operator_busy_pct": 100 * s.op_busy_s / (p.operators * p.shift_min * MIN),
    }
