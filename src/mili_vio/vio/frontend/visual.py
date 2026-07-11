"""Visual front-end: ORB/BRIEF binary descriptor extraction and matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from mili_vio.types import BinaryDescriptor


@dataclass
class KeypointObservation:
    keypoint_id: int
    uv: NDArray[np.float64]
    descriptor: BinaryDescriptor
    response: float


@dataclass
class FeatureMatch:
    query_id: int
    train_id: int
    distance: int
    query_kp: KeypointObservation
    train_kp: KeypointObservation


class VisualFrontend:
    """ORB/BRIEF feature extraction with Hamming-distance matching."""

    def __init__(
        self,
        descriptor_type: Literal["orb", "brief"] = "orb",
        max_features: int = 500,
        hamming_threshold: int = 50,
    ) -> None:
        self.descriptor_type = descriptor_type
        self.max_features = max_features
        self.hamming_threshold = hamming_threshold
        self._detector, self._extractor, self._matcher = self._create_cv_modules(descriptor_type)

    def _create_cv_modules(self, descriptor_type: str):
        if descriptor_type == "brief":
            try:
                detector = cv2.FastFeatureDetector_create(threshold=20)
                extractor = cv2.xfeatures2d.BriefDescriptorExtractor_create(bytes=16)
            except AttributeError:
                detector = cv2.ORB_create(nfeatures=self.max_features)
                extractor = detector
        else:
            detector = cv2.ORB_create(nfeatures=self.max_features)
            extractor = detector
        return detector, extractor, None

    def extract(self, image: NDArray[np.uint8]) -> list[KeypointObservation]:
        if self.descriptor_type == "brief" and self._extractor is not self._detector:
            kps = self._detector.detect(image, None)
            kps, descs = self._extractor.compute(image, kps)
        else:
            kps, descs = self._detector.detectAndCompute(image, None)

        if descs is None or not kps:
            return []

        observations: list[KeypointObservation] = []
        for i, (kp, desc) in enumerate(zip(kps, descs)):
            bits = self._to_binary_bits(desc)
            observations.append(
                KeypointObservation(
                    keypoint_id=i,
                    uv=np.array([kp.pt[0], kp.pt[1]], dtype=np.float64),
                    descriptor=BinaryDescriptor(bits=bits, keypoint_id=i),
                    response=float(kp.response),
                )
            )
        return observations

    def match(
        self,
        query: list[KeypointObservation],
        train: list[KeypointObservation],
        ratio_test: float = 0.75,
    ) -> list[FeatureMatch]:
        if not query or not train:
            return []

        matches: list[FeatureMatch] = []
        for qi, qkp in enumerate(query):
            best_dist, best_j, second_dist = 256, -1, 256
            for ti, tkp in enumerate(train):
                d = qkp.descriptor.hamming_distance(tkp.descriptor)
                if d < best_dist:
                    second_dist = best_dist
                    best_dist, best_j = d, ti
                elif d < second_dist:
                    second_dist = d

            if best_j < 0 or best_dist > self.hamming_threshold:
                continue
            if second_dist < 256 and best_dist >= ratio_test * second_dist:
                continue

            matches.append(
                FeatureMatch(
                    query_id=qi,
                    train_id=best_j,
                    distance=best_dist,
                    query_kp=query[qi],
                    train_kp=train[best_j],
                )
            )
        return matches

    def hamming_match_descriptors(
        self,
        query: list[BinaryDescriptor],
        train: list[BinaryDescriptor],
        threshold: Optional[int] = None,
    ) -> list[tuple[int, int, int]]:
        """Brute-force Hamming matching between binary descriptors."""
        thr = threshold or self.hamming_threshold
        results: list[tuple[int, int, int]] = []
        for qi, qd in enumerate(query):
            best_dist, best_j = 256, -1
            for ti, td in enumerate(train):
                d = qd.hamming_distance(td)
                if d < best_dist:
                    best_dist, best_j = d, ti
            if best_j >= 0 and best_dist <= thr:
                results.append((qi, best_j, best_dist))
        return results

    @staticmethod
    def _to_binary_bits(desc: NDArray[np.uint8]) -> NDArray[np.uint8]:
        flat = np.unpackbits(desc.flatten())
        if len(flat) >= 128:
            return flat[:128].astype(np.uint8)
        padded = np.zeros(128, dtype=np.uint8)
        padded[: len(flat)] = flat
        return padded

    @staticmethod
    def _bits_to_cv_desc(bits: NDArray[np.uint8]) -> NDArray[np.uint8]:
        packed = np.packbits(bits)
        return packed.astype(np.uint8).reshape(1, -1)

    def repeatability(self, image_a: NDArray[np.uint8], image_b: NDArray[np.uint8]) -> float:
        """Compute descriptor repeatability between two frames."""
        fa = self.extract(image_a)
        fb = self.extract(image_b)
        if not fa or not fb:
            return 0.0
        matches = self.match(fa, fb)
        return len(matches) / min(len(fa), len(fb))
