Planka Auto-Archiver
Overview

Planka Auto-Archiver is a Python automation tool that solves a common limitation in the Planka project management platform. It automatically moves cards from the "Done" column of active boards to corresponding archive columns on a designated "Archive" board, effectively clearing completed tasks while maintaining historical records.
The Problem

Planka is an excellent open-source alternative to Trello, but it lacks a built-in feature to automatically archive completed tasks. This leads to cluttered boards where old completed cards accumulate in "Done" columns, making it difficult to focus on current work.
The Solution

This script provides intelligent automation that:

    Scans multiple project boards for cards in the "Done" column (configurable name)

    Filters cards older than a specified number of days (default: 14 days)

    Moves them to a dedicated "Archive" board with department-specific columns

    Runs automatically via systemd/cron on a daily schedule

Key Features

    ✅ Cross-board movement - Properly handles Planka's API requirements for moving cards between different boards

    ✅ Multi-project support - Processes multiple source boards with department-specific archive columns

    ✅ Configurable retention - Adjustable archive threshold (days since last update)

    ✅ Safe operation - Includes card existence checks and comprehensive error handling

    ✅ Detailed logging - Complete audit trail of all operations

    ✅ Systemd/cron ready - Production-ready scheduling setup included

Installation & Setup
1. Clone and Configure
```bash

git clone https://github.com/yourusername/planka-auto-archiver.git
cd planka-auto-archiver
```
Edit the configuration section in archive.py:
```python

PLANKA_URL = "http://your-planka-server:port"
USERNAME = "archive_bot_username"
PASSWORD = "secure_password"
ARCHIVE_DAYS = 14
ARCHIVE_BOARD_ID = "your_archive_board_id"

ARCHIVE_MAPPING = {
    "source_board_id_1": "archive_column_id_1",
    "source_board_id_2": "archive_column_id_2",
}
```
2. Find Board/Column IDs

Use the included diagnostic script to identify IDs:
```bash

python3 archive-diag.py
```
3. Test the Script
```bash

python3 archive.py
```
4. Schedule Automatic Execution

Option A: Systemd (Recommended)
```bash

sudo cp systemd/* /etc/systemd/system/
sudo systemctl enable --now planka-archiver.timer
```
Option B: Cron
```bash

# Add to crontab (runs daily at 3:00 AM)
0 3 * * * /usr/bin/python3 /path/to/planka_archiver.py
```
API Compatibility Notes

This script specifically handles Planka's API limitations:

    Endpoint quirks: Some endpoints return HTML instead of JSON in certain Planka versions

    Cross-board moves: Requires both boardId and listId parameters in PATCH requests

    Authentication: Uses token-based authentication with proper header configuration

Troubleshooting

Common issues and solutions are documented in TROUBLESHOOTING.md, including:

    "List not found" errors during cross-board moves

    API returning HTML instead of JSON

    Permission and authentication problems

Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.
License

MIT License
Acknowledgments

    Built for Planka community

    Inspired by real workflow needs in team project management

    Thanks to all contributors and testers

Perfect for: Teams using Planka who want to maintain clean boards while preserving task history through automated archival.
