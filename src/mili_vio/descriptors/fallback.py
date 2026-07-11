"""Software fallback extractor (ORB/BRIEF) for development without BNN."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from numpy.typing import NDArray

from mili_vio.types import BinaryDescriptor


@dataclass
class FallbackResult:
    descriptors: list[BinaryDescriptor]
    keypoints_uv: list[NDArray[np.float64]]
    responses: list[float]


class SoftwareFallbackExtractor:
    """ORB/BRIEF fallback when BNN hardware is unavailable."""

    def __init__(
        self,
        descriptor_type: Literal["orb", "brief"] = "orb",
        max_keypoints: int = 200,
    ) -> None:
        self.descriptor_type = descriptor_type
        self.max_keypoints = max_keypoints
        self._detector, self._extractor = self._init_modules(descriptor_type)

    def _init_modules(self, descriptor_type: str):
        if descriptor_type == "brief":
            try:
                return (
                    cv2.FastFeatureDetector_create(threshold=20),
                    cv2.xfeatures2d.BriefDescriptorExtractor_create(bytes=16),
                )
            except AttributeError:
                orb = cv2.ORB_create(nfeatures=self.max_keypoints)
                return orb, orb
        orb = cv2.ORB_create(nfeatures=self.max_keypoints)
        return orb, orb

    def extract(
        self,
        image: NDArray[np.uint8],
        max_keypoints: int | None = None,
    ) -> FallbackResult:
        limit = min(max_keypoints or self.max_keypoints, self.max_keypoints)

        if self.descriptor_type == "brief" and self._extractor is not self._detector:
            kps = self._detector.detect(image, None)
            kps = sorted(kps, key=lambda k: k.response, reverse=True)[:limit]
            kps, descs = self._extractor.compute(image, kps)
        else:
            kps, descs = self._detector.detectAndCompute(image, None)

        if descs is None or not kps:
            return FallbackResult([], [], [])

        kps = sorted(kps, key=lambda k: k.response, reverse=True)[:limit]
        if self.descriptor_type != "brief" or self._extractor is self._detector:
            _, descs = self._detector.compute(image, kps)

        descriptors: list[BinaryDescriptor] = []
        keypoints_uv: list[NDArray[np.float64]] = []
        responses: list[float] = []

        for i, (kp, desc) in enumerate(zip(kps, descs)):
            bits = np.unpackbits(desc.flatten())[:128].astype(np.uint8)
            if len(bits) < 128:
                padded = np.zeros(128, dtype=np.uint8)
                padded[: len(bits)] = bits
                bits = padded
            descriptors.append(BinaryDescriptor(bits=bits, keypoint_id=i))
            keypoints_uv.append(np.array([kp.pt[0], kp.pt[1]], dtype=np.float64))
            responses.append(float(kp.response))

        return FallbackResult(descriptors, keypoints_uv, responses)
