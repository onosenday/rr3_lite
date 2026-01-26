# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.3] - 2026-01-26

### Added
- **Lobby Idle Timeout**: Implemented a 120-second timeout for the GAME_LOBBY state.
- **Auto Restart**: If the bot remains idle in the lobby for more than 2 minutes, it will automatically restart the game to ensure continued operation.

## [1.3.2] - 2026-01-23

### Fixed
- **Session Gold Display**: Fixed the session gold counter in the UI to accurately reflect gold earned in the current session.

### Added
- **UI Version Display**: The program version is now prominently displayed in the main window title.

## [1.3.1] - 2026-01-22

### Fixed
- **Timeout Recovery Logic**: Now correctly detects REWARD screen (coins) after a timeout/recovery sequence, preventing false STUCK_AD states when the game resumes directly to the reward count.

## [1.3.0] - 2026-01-22

### Added
- **STUCK_AD State**: New dedicated recovery state when the bot gets stuck in an ad after timeout.
- **Corner Change Detection**: New `detect_corner_changes()` function in `vision.py` to detect when something appears in screen corners.
- **Enhanced FF Templates**: `generate_ff_templates()` now generates multiple variants:
  - `>>` simple (without bar)
  - `>>|` with vertical bar
  - Filled and outline versions
  - Multiple line thicknesses
  - Inverted versions (black/white)
- **Escape Sequence**: Post-timeout escape sequence: BACK x2 → HOME → return to game.
- **Corner Change Boost**: When corner changes are detected, FF detection requires only 2 frames instead of 3.

### Changed
- **FF Detection Threshold**: Reduced from 0.70 to 0.60 for more tolerance.
- **FF Persistence**: Increased from 2 to 3 frames (compensates for lower threshold).
- **Timeout Recovery**: No longer assumes GAME_LOBBY without positive anchor confirmation.

### Fixed
- **False GAME_LOBBY Transitions**: Bot no longer incorrectly transitions to GAME_LOBBY when still stuck in an ad.

## [1.2.0] - 2026-01-18

### Added
- **Complete i18n System**: All UI elements now translate when changing language.
- **Translated Log Messages**: Terminal log messages now display in the selected language.
- **Calendar Legend Translations**: Added missing `calendar_no_activity` and `calendar_with_activity` keys.
- **Log Translation Keys**: Added 15+ translation keys for bot log messages across all 5 languages.
- **Bilingual README**: New GitHub README with English and Spanish sections.
- **Separate Instruction Files**: `instructions.md` (EN) and `instrucciones.md` (ES).

### Fixed
- **Stat Labels Not Translating**: Fixed initialization order bug where `stat_title_labels` was created after `_setup_ui()`.
- **Missing WiFi/Brightness Translations**: Added `lbl_wifi_label` and `lbl_brightness_label` to `_refresh_all_texts()`.
- **build.bat Windows Compatibility**: Removed invalid PNG icon (PyInstaller requires .ico format).

### Changed
- **build.bat**: Added `--hidden-import "i18n"` for proper module bundling.
- **_create_stat_block()**: Now accepts `translation_key` parameter to enable dynamic label updates.

## [1.1.0] - 2026-01-16

### Fixed
- **Google Survey Logic**: Improved detection of the "Skip" button after clicking "X" to ensure surveys are properly bypassed.
- **Fast Forward Detection**: Lowered the detection threshold for the fast forward button in `vision.py` to improve ad skipping success rate.
- **Black Screen Recovery**: Implemented double-tap HOME for persistent black screens to force context recovery.

### Added
- **Graph & Calendar Updates**: Added real-time updates for the gold history graph and the daily calendar in the GUI.

### Changed
- **Wait Times**: General adjustment of `time.sleep` calls in the main loop for better stability.

## [1.0.0] - 2026-01-11

### Added
- **Initial Release**: Launched RR3-lite as an independent, lightweight version of the bot.
- **Independence**: Project now has its own git repository, virtual environment, and `requirements.txt`.
- **Core Features**:
    - Automatic ad monitoring.
    - Timezone changing automation.
    - OCR-based text detection (Tesseract).
    - GUI with stats.
    - No ML dependency (removed TensorFlow/Keras).
