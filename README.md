# Clean WhatsApp 1.0.0 for Termux

Clean WhatsApp is a simple Termux app for Android that helps free up phone storage by cleaning old WhatsApp media.

It is designed for regular users:

- It shows a preview before changing any file.
- It uses simple cleanup profiles.
- It can move old files to a trash folder before permanent deletion.
- Permanent deletion requires an explicit confirmation word.
- It keeps operation records so files moved to trash can be restored.
- The interface supports English, Portuguese, Spanish, and French.
- It can update itself from the main menu when installed from Git.
- From the second launch onward, it quietly checks for updates and only shows a message when a new version is available.
- It shows how much storage can be freed before applying cleanup.
- It lets users filter images, videos, audio, stickers, sent media, and hidden media before scanning.

## Supported languages

On first launch, the app asks the user to choose a language:

- English
- Portuguese - Brazil
- Spanish
- French

The language can be changed later in `Settings > Change language`.

## Where it looks for WhatsApp media

The app tries to detect common WhatsApp folders:

```text
/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media
/storage/emulated/0/Android/media/com.whatsapp.w4b/WhatsApp Business/Media
/storage/emulated/0/WhatsApp/Media
```

If your phone uses another folder, change it from the app settings.

## Install or update in Termux

Quick install:

```bash
pkg update && pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/danisaia/clean_whatsapp/main/install.sh | bash
```

After that, open Clean WhatsApp with:

```bash
clean-whatsapp
```

Manual install:

1. Open Termux.

2. Allow storage access:

```bash
termux-setup-storage
```

3. Install Python and Git if needed:

```bash
pkg update
pkg install python git
```

4. Clone the repository:

```bash
git clone https://github.com/danisaia/clean_whatsapp.git
```

5. Enter the project folder:

```bash
cd clean_whatsapp
```

6. Run the app:

```bash
python3 scripts/clean_whatsapp.py
```

If you already cloned the project before, update it with:

```bash
cd clean_whatsapp
git pull origin main
```

## Start with a shorter command

From the project folder, run once:

```bash
bash install-shortcut.sh
```

After that, open the app from any folder with:

```bash
clean-whatsapp
```

If you prefer not to install the shortcut, run it from the project folder:

```bash
./clean-whatsapp
```

If `./clean-whatsapp` shows `Permission denied`, run:

```bash
chmod +x clean-whatsapp install-shortcut.sh
```

## Main menu

```text
1) Analyze and clean
2) Settings
3) Restore files from trash
4) Update Clean WhatsApp
5) Help
0) Exit
```

Start with `Analyze and clean`. The app will show:

- Files that will be kept.
- Files that can be moved to trash.
- Files that can be deleted permanently.
- The amount of storage that can be freed.
- A preview grouped by media category.
- The largest cleanup candidates.

After the preview, the user chooses whether to apply the cleanup.

## Cleanup profiles

The app has three simple profiles:

- `Safe`: keeps 60 days, moves 61 to 180 days to trash, and only suggests deleting above 180 days.
- `Balanced`: keeps 30 days, moves 31 to 90 days to trash, and only suggests deleting above 90 days.
- `Free more space`: keeps 14 days, moves 15 to 45 days to trash, and only suggests deleting above 45 days.

The user can also set custom day limits.

## Optional folders

In settings, the user can include or exclude:

- `Sent`: media sent to other people.
- `Private`: media hidden from the gallery.

For safety, `Private` is disabled by default.

## Restore

Files moved to trash can be restored from:

```text
3) Restore files from trash
```

Files deleted permanently cannot be restored by this app.

## Config and records

Configuration:

```text
~/.config/clean-whatsapp/config.json
```

Operation records:

```text
~/.local/share/clean-whatsapp/logs/
```

Trash folders are created next to the WhatsApp `Media` folder:

```text
clean_whatsapp_trash_YYYYMMDD_HHMMSS
```

## User manuals

Simple user manuals are available in four languages:

- `user_manual_en.txt`
- `user_manual_pt.txt`
- `user_manual_es.txt`
- `user_manual_fr.txt`

## Changelog and license

- Changelog: `CHANGELOG.md`
- License: `LICENSE`

## Check syntax

```bash
python3 -m py_compile scripts/clean_whatsapp.py
```

## Run tests

```bash
python3 -m unittest
```

## License

MIT License.

**Author:** Daniel Ito Isaia
