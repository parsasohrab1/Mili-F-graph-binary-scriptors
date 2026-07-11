"""Loop closure detection using binary descriptor matching."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mili_vio.vio.frontend.visual import KeypointObservation, VisualFrontend


@dataclass
class Keyframe:
    index: int
    timestamp_ns: int
    features: list[KeyframeObservation]
    position: NDArray[np.float64]
    rotation: NDArray[np.float64]


@dataclass
class KeyframeObservation:
    observation: KeypointObservation


@dataclass
class LoopClosureCandidate:
    query_index: int
    match_index: int
    num_matches: int
    measured_position: NDArray[np.float64]
    measured_rotation: NDArray[np.float64]


class LoopClosureDetector:
    def __init__(
        self,
        min_keyframe_gap: int = 30,
        hamming_threshold: int = 50,
        min_loop_matches: int = 15,
        frontend: VisualFrontend | None = None,
    ) -> None:
        self.min_keyframe_gap = min_keyframe_gap
        self.hamming_threshold = hamming_threshold
        self.min_loop_matches = min_loop_matches
        self.frontend = frontend or VisualFrontend(hamming_threshold=hamming_threshold)
        self.keyframes: list[Keyframe] = []

    def add_keyframe(
        self,
        index: int,
        timestamp_ns: int,
        features: list[KeyframeObservation],
        position: NDArray[np.float64],
        rotation: NDArray[np.float64],
    ) -> list[LoopClosureCandidate]:
        kf = Keyframe(index, timestamp_ns, features, position.copy(), rotation.copy())
        self.keyframes.append(kf)

        candidates: list[LoopClosureCandidate] = []
        if len(self.keyframes) < 2:
            return candidates

        query_feats = [f.observation for f in features]
        for past in self.keyframes[:-1]:
            if index - past.index < self.min_keyframe_gap:
                continue
            past_feats = [f.observation for f in past.features]
            matches = self.frontend.match(query_feats, past_feats)
            if len(matches) >= self.min_loop_matches:
                rel_pos = past.position - position
                rel_rot = rotation.T @ past.rotation
                candidates.append(
                    LoopClosureCandidate(
                        query_index=index,
                        match_index=past.index,
                        num_matches=len(matches),
                        measured_position=rel_pos,
                        measured_rotation=rel_rot,
                    )
                )
        return candidates
