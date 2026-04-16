# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.1.0] - 2026-04-16

### Added
- P0 output evasion protocol - large outputs (>4KB) automatically diverted to disk
- Apple-style README with architecture diagrams
- One-click installation script (`install.sh`)
- Competitive comparison table (vs LiteLLM, PortKey)
- CI/CD badge in README
- Competitive comparison table

### Fixed
- OMO plugin streaming EOF errors
- API server missing required HTTP headers for SSE
- Daemon health check loop spurious warnings
- Missing `activate_profile` method in SmartModelDispatcher

### Changed
- README fully universalized - removed all private branding
- Version bumped from 5.0.0 → 5.1.0
- API server startup message cleaned

## [5.0.0] - 2026-04-09

### Added
- Brain-body separation architecture (selector_core + dispatcher)
- Intent-based routing with keyword detection
- Streaming output with keep-alive headers
- OpenAI-compatible API gateway (`api_server.py`)

### Changed
- Refactored `smart_model_dispatcher.py` for cleaner separation of concerns

## [4.2.1] - 2026-04-08

### Changed
- Restored `gemini-3.1-pro-preview` as default text model

## [4.2.0] - 2026-04-08

### Added
- Support for `gemini-2.5-pro` and `gemini-2.5-flash` models
- Configuration fallback mechanism

## [4.1.3] - 2026-04-06

### Changed
- Refactored `smart_model_dispatcher.py` - removed redundant logic

## [4.1.2] - 2026-04-06

### Fixed
- CLI output now returns pure model ID (compatible with OpenCode parsing)

## [4.1.1] - 2026-04-06

### Fixed
- OpenCode integration issues
- Model smart switching optimization

## [4.1.0] - 2026-04-02

### Added
- Physical dual-engine architecture with intent直达

## [4.0.0] - 2026-03-02

### Added
- YAML configuration support
- Performance telemetry
- Dynamic degradation

## [3.1.0] - 2026-03-02

### Added
- Configuration-driven architecture
- Zero-code model addition via `models_config.json`

## [3.0.0] - 2026-03-01

### Added
- Hexagonal architecture
- Adapter pattern for providers

## [2.2.0] - 2026-02-27

### Added
- Dual engine architecture
- Circuit breaker and degradation
- Concurrent optimization
- 4h speed cache expiration
- `op engine` command

## [2.1.0] - 2026-02-26

### Added
- API Server module (OpenAI-compatible interface)
- `op api` command

## [2.0.0] - 2026-02-25

### Added
- Manual model selection → auto priority recommendation
- 24h TTL
- Auto-switch after 3 consecutive failures
- `op auto/reset` commands
- Long text degradation strategy
- Persistent speed memory

## [1.0.0] - 2025-01-01

### Added
- Initial release - smart model selection + failover
