# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
