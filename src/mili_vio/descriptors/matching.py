"""Optimized binary descriptor matching with Hamming distance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mili_vio.types import BinaryDescriptor


# Popcount lookup for 8-bit values
_POPCOUNT_LUT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


@dataclass
class BinaryMatch:
    query_idx: int
    train_idx: int
    distance: int


class BinaryMatcher:
    """
    Optimized Hamming-distance matcher for 128-bit binary descriptors.

    Uses packed XOR + LUT popcount for batch efficiency.
    """

    def __init__(
        self,
        hamming_threshold: int = 50,
        ratio_test: float = 0.75,
    ) -> None:
        self.hamming_threshold = hamming_threshold
        self.ratio_test = ratio_test

    def hamming_distance(self, a: BinaryDescriptor, b: BinaryDescriptor) -> int:
        return int(self.batch_hamming(
            a.bits.reshape(1, -1),
            b.bits.reshape(1, -1),
        )[0, 0])

    @staticmethod
    def batch_hamming(bits_a: np.ndarray, bits_b: np.ndarray) -> np.ndarray:
        """Compute pairwise Hamming distances. bits shape: (N, 128) and (M, 128)."""
        packed_a = np.packbits(bits_a, axis=1)
        packed_b = np.packbits(bits_b, axis=1)
        n, m = packed_a.shape[0], packed_b.shape[0]
        distances = np.zeros((n, m), dtype=np.int32)
        for i in range(n):
            xor_row = packed_a[i : i + 1] ^ packed_b
            distances[i] = _POPCOUNT_LUT[xor_row].sum(axis=1)
        return distances

    def match(
        self,
        query: list[BinaryDescriptor],
        train: list[BinaryDescriptor],
    ) -> list[BinaryMatch]:
        if not query or not train:
            return []

        q_bits = np.vstack([d.bits for d in query])
        t_bits = np.vstack([d.bits for d in train])
        dist_matrix = self.batch_hamming(q_bits, t_bits)

        matches: list[BinaryMatch] = []
        for i in range(len(query)):
            row = dist_matrix[i]
            best_j = int(np.argmin(row))
            best_d = int(row[best_j])
            if best_d > self.hamming_threshold:
                continue

            if len(train) > 1:
                row_copy = row.copy()
                row_copy[best_j] = 256
                second_d = int(np.min(row_copy))
                if best_d >= self.ratio_test * second_d:
                    continue

            matches.append(BinaryMatch(i, best_j, best_d))
        return matches

    def match_cross_check(
        self,
        query: list[BinaryDescriptor],
        train: list[BinaryDescriptor],
    ) -> list[BinaryMatch]:
        """Mutual nearest-neighbor matching for higher precision."""
        forward = {(m.query_idx, m.train_idx): m for m in self.match(query, train)}
        reverse = self.match(train, query)
        reverse_set = {(m.train_idx, m.query_idx) for m in reverse}
        return [
            forward[(qi, ti)]
            for qi, ti in forward
            if (qi, ti) in reverse_set
        ]
