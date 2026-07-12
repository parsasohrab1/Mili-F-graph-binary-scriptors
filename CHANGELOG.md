# Changelog

All notable changes to **mili-vio** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI (fast pytest, embedded smoke, Phase 6 on main)
- Operator guide (`docs/OPERATOR_GUIDE.md`)
- API integration guide (`docs/API_INTEGRATION.md`)
- Product README (replaces inline SRS as primary landing page)
- Release process documentation (`docs/RELEASE.md`)

## [0.1.0] - 2026-07-12

### Added
- **Phase 0–5** — Python VIO platform: ORB/BRIEF frontend, factor graph (GTSAM/SciPy), EKF baseline, loop closure
- **FR-1** — BNN SPI protocol, HAL transports, SRS hardware validation
- **FR-2** — Sliding-window factor graph, 4 SRS scenarios, g2o embedded Gauss-Newton
- **FR-3** — Event-driven cooperative sharing, UDP transport, 2–12 drone simulation
- **Integrated runtime** — `mili-vio-run`, 69-byte FC binary frame, multi-drone pipeline
- **Embedded** — STM32H7 host sim, HAL (DCMI, BMI088, DWT), FreeRTOS task graph, acceptance tests
- **Phase 6** — `mili-vio-validate`, dataset download script, unified SRS report
- **Tests** — 23 pytest modules; embedded CTest (factor_graph, memory, pipeline)
- **Docs** — PHASE1–6 technical guides

### Known limitations
- EuRoC/TUM-VI require manual or scripted download
- STM32 production HAL stubs (DCMI DMA, BMI088 SPI) — host sim default
- Field tests (GPS-denied, fleet) documented as manual checklists
- GTSAM optional; Windows uses SciPy backend

[Unreleased]: https://github.com/ithub-ai/Mili-F-graph-binary-scriptors/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ithub-ai/Mili-F-graph-binary-scriptors/releases/tag/v0.1.0
