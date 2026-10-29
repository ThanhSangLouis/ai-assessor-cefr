"""Zone layout for the class diagram: boxes grouped in framed zones, edges routed
orthogonally on a grid so they go around boxes and keep apart from each other.

The column router in `gen_class_diagram.py` lays every edge in the gutters
between columns, so edges between distant columns bunch into the same gutters.
Here each edge is an A* search on a 10-point grid:

  - boxes (with a 10-point margin) are walls;
  - running along a cell another edge already runs along costs a lot, running
    next to one costs a little, crossing one costs almost nothing -- so edges
    keep apart and cross at right angles instead of sharing a line;
  - each bend costs, so a path stays as straight as the walls allow;
  - cutting through a zone neither end belongs to costs, so edges between
    zones keep to the corridors between frames.

Ports are spread along each box side and ordered by where the other end lies,
so two edges leaving one side do not cross right at the box.
"""

from __future__ import annotations

import heapq
import math

GRID = 10
COL_X0, COL_DX = 40, 440  # box column i starts at COL_X0 + i * COL_DX
ROW_GAP = 70  # between two boxes stacked in one column
ZONE_PAD, ZONE_TITLE = 30, 50
CORRIDOR = 90  # between the top row of zones and the bottom row

# Costs of the router, in grid steps.
BEND = 10
SAME_AXIS = 300  # running on top of another edge: go round instead
NEXT_TO = (20, 6)  # running one / two cells beside another edge
CROSS = 3
FOREIGN_ZONE = 2
TITLE_STRIP = 15
ON_FRAME = 15  # running along a zone frame reads as part of the frame


def place(zones, height_of, width):
    """Box geometry and zone frames from `zones`.

    `zones` is a list of (key, title, row, columns) where columns is a list of
    (column index, items); an item is a box id, stacked under the one before,
    or (box id, dy) to put it `dy` below the top of its row, or (box id, other)
    to put it level with a box of an earlier column.
    """
    geo: dict[str, tuple[int, int, int]] = {}
    zone_of: dict[str, str] = {}
    row_top = {0: ZONE_PAD + ZONE_TITLE + 10}

    def stack(row):
        for key, _title, r, columns in zones:
            if r != row:
                continue
            for col, items in columns:
                x, y = COL_X0 + col * COL_DX, row_top[row]
                for item in items:
                    cid, dy = item if isinstance(item, tuple) else (item, None)
                    if isinstance(dy, str):
                        y = geo[dy][1]  # level with a box placed before
                    elif dy is not None:
                        y = row_top[row] + dy
                    h = height_of(cid)
                    geo[cid] = (x, y, h)
                    zone_of[cid] = key
                    y += h + ROW_GAP

    stack(0)
    top_bottom = max(y + h for _x, y, h in geo.values())
    row_top[1] = top_bottom + ZONE_PAD + CORRIDOR + ZONE_TITLE
    stack(1)

    frames = {}
    for key, title, _r, _cols in zones:
        ids = [c for c, z in zone_of.items() if z == key]
        x0 = min(geo[c][0] for c in ids) - ZONE_PAD
        y0 = min(geo[c][1] for c in ids) - ZONE_PAD - ZONE_TITLE
        x1 = max(geo[c][0] for c in ids) + width + ZONE_PAD
        y1 = max(geo[c][1] + geo[c][2] for c in ids) + ZONE_PAD
        frames[key] = (title, x0, y0, x1 - x0, y1 - y0)
    return geo, zone_of, frames


def _sides(s, d, width):
    """Side of the source box the edge leaves by, and side of the target it enters."""
    sx, sy, sh = s
    dx, dy, dh = d
    if dx >= sx + width + 40:
        return "R", "L"
    if dx + width <= sx - 40:
        return "L", "R"
    return ("B", "T") if dy > sy + sh / 2 else ("T", "B")


NORMAL = {"R": (1, 0), "L": (-1, 0), "B": (0, 1), "T": (0, -1)}


def _side_span(box, side, width):
    x, y, h = box
    if side in "LR":
        fixed = x + width if side == "R" else x
        return fixed, y, y + h
    fixed = y + h if side == "B" else y
    return fixed, x, x + width


def route(edges, geo, zone_of, frames, width):
    """Paths for `edges` [(src, dst, ...)]: index -> (points, src_side, dst_side).

    `points` starts on the source box border and ends on the target's.
    """
    sides = {i: _sides(geo[e[0]], geo[e[1]], width) for i, e in enumerate(edges)}

    def centre(cid):
        x, y, h = geo[cid]
        return x + width / 2, y + h / 2

    # ---- ports: spread along each side, ordered by where the far end lies
    slots: dict[tuple[str, str], list[tuple[float, int, int]]] = {}
    for i, e in enumerate(edges):
        so, si = sides[i]
        far_d, far_s = centre(e[1]), centre(e[0])
        slots.setdefault((e[0], so), []).append((far_d[1] if so in "LR" else far_d[0], i, 0))
        slots.setdefault((e[1], si), []).append((far_s[1] if si in "LR" else far_s[0], i, 1))
    port: dict[tuple[int, int], tuple[float, float]] = {}
    for (cid, side), items in slots.items():
        fixed, lo, hi = _side_span(geo[cid], side, width)
        n = len(items)
        step = max(GRID, GRID * math.floor(min(40, (hi - lo - 20) / n) / GRID))
        mid = GRID * round((lo + hi) / 2 / GRID)
        first = mid - step * (n - 1) / 2
        first = GRID * round(first / GRID)
        for k, (_key, i, end) in enumerate(sorted(items)):
            along = first + k * step
            port[(i, end)] = (fixed, along) if side in "LR" else (along, fixed)

    # ---- grid
    max_x = max(f[1] + f[3] for f in frames.values()) + 200
    max_y = max(f[2] + f[4] for f in frames.values()) + 200
    nx, ny = int(max_x // GRID) + 1, int(max_y // GRID) + 1
    wall = [[False] * ny for _ in range(nx)]
    for x, y, h in geo.values():
        for gx in range(max(0, (x - 10) // GRID), min(nx, (x + width + 10) // GRID + 1)):
            for gy in range(max(0, int(y - 10) // GRID), min(ny, int(y + h + 10) // GRID + 1)):
                if x - 10 <= gx * GRID <= x + width + 10 and y - 10 <= gy * GRID <= y + h + 10:
                    wall[gx][gy] = True
    zone_at = [[None] * ny for _ in range(nx)]
    title_at = [[False] * ny for _ in range(nx)]
    frame_at = [[False] * ny for _ in range(nx)]
    for key, (_t, fx, fy, fw, fh) in frames.items():
        for gx in range(int(fx // GRID), int((fx + fw) // GRID) + 1):
            for gy in range(int(fy // GRID), int((fy + fh) // GRID) + 1):
                if 0 <= gx < nx and 0 <= gy < ny:
                    zone_at[gx][gy] = key
                    if gy * GRID < fy + ZONE_TITLE - 10:
                        title_at[gx][gy] = True
                    if (
                        min(abs(gx * GRID - fx), abs(gx * GRID - fx - fw)) <= GRID
                        or min(abs(gy * GRID - fy), abs(gy * GRID - fy - fh)) <= GRID
                    ):
                        frame_at[gx][gy] = True
    used_h = [[0] * ny for _ in range(nx)]
    used_v = [[0] * ny for _ in range(nx)]

    def stub(p, side):
        """First grid point 20 or more points out from a port."""
        x, y = p
        if side == "R":
            return (math.ceil((x + 20) / GRID), round(y / GRID))
        if side == "L":
            return (math.floor((x - 20) / GRID), round(y / GRID))
        if side == "B":
            return (round(x / GRID), math.ceil((y + 20) / GRID))
        return (round(x / GRID), math.floor((y - 20) / GRID))

    def search(a, b, own):
        """A* from grid point a to b; state carries the axis of the last step."""
        moves = ((1, 0, 0), (-1, 0, 0), (0, 1, 1), (0, -1, 1))
        start = (a[0], a[1], -1)
        dist = {start: 0}
        back = {}
        heap = [(abs(a[0] - b[0]) + abs(a[1] - b[1]), 0, start)]
        while heap:
            _f, g, state = heapq.heappop(heap)
            x, y, axis = state
            if (x, y) == b:
                path = [(x, y)]
                while state in back:
                    state = back[state]
                    path.append(state[:2])
                return path[::-1]
            if g > dist.get(state, 1e18):
                continue
            for mx, my, ax in moves:
                cx, cy = x + mx, y + my
                if not (0 <= cx < nx and 0 <= cy < ny) or wall[cx][cy]:
                    continue
                cost = 1 + (BEND if axis not in (-1, ax) else 0)
                if ax == 0:
                    cost += SAME_AXIS * used_h[cx][cy] + CROSS * used_v[cx][cy]
                    cost += sum(
                        NEXT_TO[abs(k) - 1] * used_h[cx][cy + k]
                        for k in (-2, -1, 1, 2)
                        if 0 <= cy + k < ny
                    )
                else:
                    cost += SAME_AXIS * used_v[cx][cy] + CROSS * used_h[cx][cy]
                    cost += sum(
                        NEXT_TO[abs(k) - 1] * used_v[cx + k][cy]
                        for k in (-2, -1, 1, 2)
                        if 0 <= cx + k < nx
                    )
                z = zone_at[cx][cy]
                if z is not None and z not in own:
                    cost += FOREIGN_ZONE
                if title_at[cx][cy]:
                    cost += TITLE_STRIP
                if frame_at[cx][cy]:
                    cost += ON_FRAME
                nxt = (cx, cy, ax)
                ng = g + cost
                if ng < dist.get(nxt, 1e18):
                    dist[nxt] = ng
                    back[nxt] = state
                    heapq.heappush(heap, (ng + abs(cx - b[0]) + abs(cy - b[1]), ng, nxt))
        return None

    def mark(path):
        for (x0, y0), (x1, y1) in zip(path, path[1:], strict=False):
            if y0 == y1:
                used_h[x0][y0] += 1
                used_h[x1][y1] += 1
            else:
                used_v[x0][y0] += 1
                used_v[x1][y1] += 1

    def reserve(p, side):
        """Mark the short run from a port out to its first grid point as used.

        Every edge's runs are reserved before any edge is routed: otherwise an
        edge routed early lays its line right where a later edge has to leave
        its box, and the two share that run.
        """
        gx, gy = stub(p, side)
        if side in "LR":
            x0 = int(p[0] // GRID)
            for x in range(min(x0, gx), max(x0, gx) + 1):
                if 0 <= x < nx and 0 <= gy < ny:
                    used_h[x][gy] += 1
        else:
            y0 = int(p[1] // GRID)
            for y in range(min(y0, gy), max(y0, gy) + 1):
                if 0 <= gx < nx and 0 <= y < ny:
                    used_v[gx][y] += 1

    for i in range(len(edges)):
        reserve(port[(i, 0)], sides[i][0])
        reserve(port[(i, 1)], sides[i][1])

    order = sorted(
        range(len(edges)),
        key=lambda i: sum(
            abs(p - q) for p, q in zip(centre(edges[i][0]), centre(edges[i][1]), strict=True)
        ),
    )
    routes = {}
    for i in order:
        src, dst = edges[i][0], edges[i][1]
        so, si = sides[i]
        p0, p1 = port[(i, 0)], port[(i, 1)]
        a, b = stub(p0, so), stub(p1, si)
        path = search(a, b, {zone_of[src], zone_of[dst]})
        if path is None:
            raise SystemExit(f"no route for {src} -> {dst}")
        mark(path)
        pts = [p0] + [(x * GRID, y * GRID) for x, y in path] + [p1]
        routes[i] = (_corners(pts), so, si)
    return routes


def _corners(pts):
    """Drop points that sit on a straight run between their neighbours."""
    out = [pts[0]]
    for prev, cur, nxt in zip(pts, pts[1:], pts[2:], strict=False):
        if (prev[0] == cur[0] == nxt[0]) or (prev[1] == cur[1] == nxt[1]):
            continue
        out.append(cur)
    out.append(pts[-1])
    return out
