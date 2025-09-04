# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Talkie is a Voice-to-Text and Text-to-Speech interactive fiction (IF) player that combines AI capabilities with classic text adventure gameplay. It can play Z-code games, Level9 adventures, and includes AI-generated imagery and audio narration.

## Core Architecture

- **IFPlayer**: Subprocess-based interactive fiction game runner (Z-code via frotz, Level9 via custom interpreter)
- **AIPlayer**: Orchestrates AI interactions between voice input, game state, and multimedia output
- **AdventureGuy**: AI assistant that provides contextual help and game guidance
- **TextToSpeech**: Audio narration using OpenAI's TTS API
- **VoiceRecorder/VoiceToText**: Speech recognition for voice commands
- **ImageGen**: AI image generation for game scenes using OpenAI's DALL-E
- **ImageDrawer**: Renders game graphics with retro CRT effects and scanlines
- **Cache**: File-based caching system for API responses and generated content

The application uses dependency injection via `lagom` Container and follows a modular architecture where components communicate through well-defined interfaces.

## Development Commands

### Testing
```bash
pytest                                    # Run all tests
pytest tests/test_cache.py -v           # Run specific test file
pytest tests/test_talkie.py::TestTalkie::test_parse_adventure_description_copyright_only -v  # Run specific test
pytest --cov=talkie --cov-report=html    # Run with coverage
```

### Code Quality
```bash
ruff format                              # Format code (run after editing Python files)
ruff check                               # Lint code
pyright                                  # Type checking
```

### Running the Application
```bash
python -m talkie                         # Run as module
talkie                                   # Run installed CLI (after pip install -e .)
```

### Building
```bash
pip install -e .                         # Install in development mode
pip install -e .[dev]                    # Install with development dependencies
```

## Key Configuration

- Configuration managed via `TalkieConfig` dataclass and YAML files
- OpenAI API integration for TTS, STT, and image generation
- PyAudio for audio playback and recording
- Pixpy for graphics rendering with retro effects
- Game files supported: .z* (Z-code), .l9 (Level9), .v* (Level9 variants)

## Important Notes

- Always run `ruff format` after editing Python files
- Game interpreters are built as external tools (frotz for Z-code, custom Level9 interpreter)
- The project includes CMake build system for C interpreters in tools/ directory
- Graphics assets and fonts are stored in talkie/data/
- Logging configured to write to talkie.log file