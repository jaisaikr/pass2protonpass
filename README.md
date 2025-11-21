# Proton Pass Migration Tool

This Python script migrates password entries from the Unix `pass` password manager to a CSV format compatible with Proton Pass import.

## Features

- Extracts passwords from the Unix `pass` password store
- Parses common fields: username, email, password, notes
- Exports to Proton Pass compatible CSV format
- Supports GPG agent passphrase preset to avoid interactive prompts

## Prerequisites

1. **Unix pass** - The password manager must be installed and configured
2. **GPG** - Required by pass for encryption/decryption
3. **Python 3.6+** - For running the migration script

## GPG Agent Configuration

To avoid interactive GPG passphrase prompts during migration, you need to enable passphrase preset in GPG agent:

1. Edit your GPG agent configuration file:
   ```bash
   ~/.gnupg/gpg-agent.conf
   ```

2. Add the following line:
   ```
   allow-preset-passphrase
   ```

3. Reload the GPG agent:
   ```bash
   gpg-connect-agent reloadagent /bye
   ```

   If the above doesn't work, you may need to restart the agent completely:
   ```bash
   gpg-connect-agent killagent /bye
   gpg-agent --daemon
   ```

## Environment Variables

The script uses the following environment variables:

- `GPG_PASSPHRASE` (optional): Your GPG passphrase. If not set, you'll be prompted to enter it
- `ENCRYPTION_KEYGRIP` (required for passphrase preset): Your GPG key's keygrip

### Finding Your Keygrip

To find your encryption keygrip:

```bash
gpg --list-secret-keys --with-keygrip
```

Look for your encryption key and copy the keygrip value.

## Usage

1. **Set environment variables** (optional but recommended):
   ```bash
   export GPG_PASSPHRASE="your-gpg-passphrase"
   export ENCRYPTION_KEYGRIP="your-keygrip-here"
   ```

2. **Run the migration script**:
   ```bash
   python migrate.py
   ```

3. **Import the generated CSV** into Proton Pass:
   - The output file will be saved to `~/.proton-migrate/protonpass.csv`
   - Import this file through the Proton Pass web interface
   - **⚠️ IMPORTANT: Delete the CSV file after importing** to protect your password data:
     ```bash
     rm ~/.proton-migrate/protonpass.csv
     ```

## Output Format

The script generates a CSV file with the following columns:
- `name`: Entry name from pass
- `url`: URL (currently empty)
- `email`: Extracted email addresses
- `username`: Extracted usernames (looks for username:, user:, login: prefixes)
- `password`: The actual password
- `note`: Any additional lines not categorized as username/email
- `totp`: TOTP codes (currently empty)
- `vault`: Vault assignment (currently empty)

## Pass Entry Format

The script expects pass entries in this format:

```
password_here
username: your_username
email: your_email@example.com
any other notes or information
```

Alternatively, simple formats like:
```
password_here
your_username
your_email@example.com
```

## File Locations

- **Input**: `~/.password-store/` (default pass store location)
- **Output**: `~/.proton-migrate/protonpass.csv`

## Troubleshooting

### GPG Passphrase Issues
- Ensure `allow-preset-passphrase` is enabled in `~/.gnupg/gpg-agent.conf`
- Verify your `ENCRYPTION_KEYGRIP` is correct
- Check that the GPG agent is running and reloaded

### Permission Issues
- Ensure you have read access to `~/.password-store/`
- Ensure you can create files in `~/.proton-migrate/`

### Missing Dependencies
- Install `pass`: Most package managers have it available
- Ensure Python 3.6+ is installed

## Cross-Platform Compatibility

This script has been tested on:
- macOS
- Linux

Windows support may require additional configuration for GPG paths and pass installation.