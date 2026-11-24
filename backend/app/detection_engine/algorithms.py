"""Core similarity algorithms: greedy string tiling, winnowing, TF-IDF, set measures."""
from __future__ import annotations

import hashlib
import heapq
import math
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Iterable, Sequence

MASK61 = (1 << 61) - 1
_BASE = 1_000_003
_sym_cache: dict[str, int] = {}


def stable_hash(text: str) -> int:
    """Deterministic 63-bit hash (safe for a signed BIGINT column)."""
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8", "replace"), digest_size=8).digest(), "big") >> 1


def _sym(s: str) -> int:
    v = _sym_cache.get(s)
    if v is None:
        v = stable_hash(s) & MASK61
        if len(_sym_cache) < 200_000:
            _sym_cache[s] = v
    return v


# --------------------------------------------------------------------------- winnowing
def kgram_hashes(symbols: Sequence[str], k: int) -> list[int]:
    """Rolling polynomial hashes of every k-gram."""
    n = len(symbols)
    if k <= 0 or n < k:
        return []
    vals = [_sym(s) for s in symbols]
    top = pow(_BASE, k - 1, MASK61)
    h = 0
    for v in vals[:k]:
        h = (h * _BASE + v) % MASK61
    out = [h]
    for i in range(k, n):
        h = ((h - vals[i - k] * top) * _BASE + vals[i]) % MASK61
        out.append(h)
    return out


def winnow(hashes: Sequence[int], w: int) -> list[tuple[int, int]]:
    """Winnowing (Schleimer et al.): select the minimum hash of each window of size ``w``.

    Returns ``(hash, position)`` fingerprints.  Any match of at least ``w + k - 1`` symbols
    is guaranteed to share at least one fingerprint.
    """
    n = len(hashes)
    if n == 0:
        return []
    if n <= w:
        m = min(range(n), key=lambda i: (hashes[i], -i))
        return [(hashes[m], m)]
    fps: list[tuple[int, int]] = []
    last = -1
    for s in range(n - w + 1):
        window = hashes[s : s + w]
        m = min(window)
        idx = s + (w - 1 - window[::-1].index(m))  # rightmost minimum
        if idx != last:
            fps.append((m, idx))
            last = idx
    return fps


def winnow_runs(
    fa: Sequence[tuple[int, int]], fb: Sequence[tuple[int, int]], k: int, max_pos: int = 4
) -> list[tuple[int, int, int]]:
    """Convert shared fingerprints into contiguous runs ``(i, j, length)`` of matching symbols."""
    pos_b: dict[int, list[int]] = defaultdict(list)
    for h, p in fb:
        if len(pos_b[h]) < max_pos:
            pos_b[h].append(p)
    pairs: list[tuple[int, int]] = []
    for h, p in fa:
        for q in pos_b.get(h, ()):
            pairs.append((p, q))
    pairs.sort(key=lambda x: (x[0] - x[1], x[0]))
    runs: list[tuple[int, int, int]] = []
    cur: list[int] | None = None  # [diag, i_start, i_end_exclusive]
    for i, j in pairs:
        diag = i - j
        if cur is not None and cur[0] == diag and i <= cur[2]:
            cur[2] = max(cur[2], i + k)
        else:
            if cur is not None:
                runs.append((cur[1], cur[1] - cur[0], cur[2] - cur[1]))
            cur = [diag, i, i + k]
    if cur is not None:
        runs.append((cur[1], cur[1] - cur[0], cur[2] - cur[1]))
    return runs


# --------------------------------------------------------------------------- greedy string tiling
def greedy_string_tiling(
    a: Sequence[str], b: Sequence[str], min_len: int, max_candidates: int = 200_000
) -> list[tuple[int, int, int]]:
    """Greedy String Tiling (Wise).  Returns non-overlapping tiles ``(i, j, length)``.

    Longest maximal matches are tiled first; each symbol of either sequence can belong to
    at most one tile, so block moves (re-ordering) are handled naturally.
    """
    la, lb = len(a), len(b)
    k = min_len
    if la < k or lb < k:
        return []
    ids: dict[str, int] = {}
    A = [ids.setdefault(s, len(ids)) for s in a]
    B = [ids.setdefault(s, len(ids)) for s in b]
    index: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for j in range(lb - k + 1):
        index[tuple(B[j : j + k])].append(j)

    heap: list[tuple[int, int, int, int]] = []
    count = 0
    for i in range(la - k + 1):
        js = index.get(tuple(A[i : i + k]))
        if not js:
            continue
        for j in js:
            if i > 0 and j > 0 and A[i - 1] == B[j - 1]:
                continue  # not left-maximal; covered by an earlier candidate
            length = k
            while i + length < la and j + length < lb and A[i + length] == B[j + length]:
                length += 1
            heap.append((-length, i, j, length))
            count += 1
            if count >= max_candidates:
                break
        if count >= max_candidates:
            break
    heapq.heapify(heap)

    marked_a = [False] * la
    marked_b = [False] * lb
    tiles: list[tuple[int, int, int]] = []
    while heap:
        _, i, j, length = heapq.heappop(heap)
        pieces: list[tuple[int, int]] = []
        start: int | None = None
        for t in range(length):
            free = not marked_a[i + t] and not marked_b[j + t]
            if free and start is None:
                start = t
            if (not free or t == length - 1) and start is not None:
                pieces.append((start, t if not free else t + 1))
                start = None
        if len(pieces) == 1 and pieces[0] == (0, length):
            if length >= k:
                for t in range(length):
                    marked_a[i + t] = True
                    marked_b[j + t] = True
                tiles.append((i, j, length))
        else:
            for s, e in pieces:
                if e - s >= k:
                    heapq.heappush(heap, (-(e - s), i + s, j + s, e - s))
    tiles.sort()
    return tiles


# --------------------------------------------------------------------------- set / sequence measures
def dice_counter(c1: Counter, c2: Counter) -> float:
    s1, s2 = sum(c1.values()), sum(c2.values())
    if s1 + s2 == 0:
        return 0.0
    inter = sum((c1 & c2).values())
    return 2.0 * inter / (s1 + s2)


def dice_sets(s1: set, s2: set) -> float:
    if not s1 and not s2:
        return 0.0
    return 2.0 * len(s1 & s2) / (len(s1) + len(s2))


def sequence_ratio(a: Sequence[str], b: Sequence[str], cap: int = 2500) -> float:
    """Order-sensitive similarity of two sequences (difflib ratio, with a cheap fallback)."""
    if not a and not b:
        return 0.0
    if len(a) > cap or len(b) > cap:
        ca = Counter(zip(a, a[1:]))
        cb = Counter(zip(b, b[1:]))
        return dice_counter(ca, cb)
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


# --------------------------------------------------------------------------- TF-IDF
class TfidfModel:
    """Smoothed TF-IDF (sub-linear tf) over arbitrary string features."""

    def __init__(self, idf: dict[str, float], default_idf: float):
        self.idf = idf
        self.default_idf = default_idf

    @classmethod
    def fit(cls, docs: Iterable[Counter]) -> "TfidfModel":
        df: Counter[str] = Counter()
        n = 0
        for d in docs:
            n += 1
            df.update(d.keys())
        idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        return cls(idf, math.log(1 + n) + 1.0)

    def vector(self, tf: Counter) -> dict[str, float]:
        vec = {t: (1.0 + math.log(c)) * self.idf.get(t, self.default_idf) for t, c in tf.items() if c > 0}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm == 0:
            return {}
        return {t: v / norm for t, v in vec.items()}


def cosine(v1: dict[str, float], v2: dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    return max(0.0, min(1.0, sum(w * v2.get(t, 0.0) for t, w in v1.items())))


def top_shared_terms(v1: dict[str, float], v2: dict[str, float], limit: int = 5) -> list[str]:
    shared = [(v1[t] * v2[t], t) for t in v1.keys() & v2.keys()]
    shared.sort(reverse=True)
    return [t for _, t in shared[:limit]]
