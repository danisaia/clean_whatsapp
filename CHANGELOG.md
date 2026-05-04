# Changelog

## 1.1.0 - 2026-05-04

- Added GB WhatsApp path to the list of detected media folders.
- Added `followlinks=False` to scanner to prevent infinite loops from symlinks.
- Added progress indicator during file scanning (updated every 500 files).
- Added elapsed time display after scan completion.
- Added write-ahead pending marker so interrupted operations are detected on next startup.
- Added cleanup of empty directories after moving files to trash.
- Added ANSI color coding to the preview output for better readability.
- Added "Cleanup history" menu option showing statistics of all past operations.
- Added safe handling of missing or corrupted log files during restore.
- Added translation keys for all new features in English, Portuguese, Spanish, and French.

## 1.0.0 - 2026-04-30

- Added a modular application structure: UI, translations, scanner, actions, config, and restore logic.
- Added language files for English, Portuguese, Spanish, and French.
- Added first-run language selection and a language option in settings.
- Added the "Update Clean WhatsApp" option to the main menu.
- Standardized the product name as Clean WhatsApp and the command as `clean-whatsapp`.
- Added user manuals in four languages.
- Added safety tests for invalid folders, permission errors, invalid config, removed files, and missing trash files.
- Added MIT license file.
- Added a one-line Termux installer.
- Added terminal screen clearing in the main screens to keep the interface easier to read.
- Added a silent startup update check after the first setup.
