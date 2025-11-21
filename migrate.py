"""Migration tool to convert Unix pass entries to Proton Pass CSV format."""
import csv
import os
import subprocess
import getpass
from dataclasses import dataclass, asdict
from typing import Optional, List

PASS_STORE="~/.password-store"
OUTPUT_FILE="~/.proton-migrate/protonpass.csv"

PROTON_HEADERS = ["name", "url", "email", "username", "password", "note", "totp", "vault"]

@dataclass
class PassContent:
    """Data class representing a password entry for Proton Pass import."""
    name: str
    password: str
    url: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    note: Optional[str] = None
    totp: Optional[str] = None

def process_pass(entry_name: str, raw_pass_content: str) -> PassContent:
    """
    Parse raw pass content into structured PassContent.

    Expected format:
    - First line: password
    - Subsequent lines: key:value pairs or standalone values
    - email: detected by presence of '@' character
    - username: detected by 'username:', 'user:', or 'login:' prefix
    - note: everything else not categorized
    """
    if not raw_pass_content:
        return PassContent(
            name=entry_name,
            password=""
        )

    lines = raw_pass_content.split('\n')
    password = lines[0].strip() if lines else ""

    email = None
    username = None
    note_lines = []

    # Process remaining lines
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Check for email (contains '@')
        if '@' in line:
            if ':' in line:
                # Format: "email: user@example.com"
                email = line.split(':', 1)[1].strip()
            else:
                # Format: "user@example.com"
                email = line.strip()
        # Check for username variants
        elif any(line.lower().startswith(prefix) for prefix in ['username:', 'user:', 'login:']):
            username = line.split(':', 1)[1].strip()
        # Everything else goes to notes
        else:
            note_lines.append(line)

    # Combine note lines, replacing literal '\n' with ' | ' to avoid CSV issues
    note = ' | '.join(note_lines) if note_lines else None

    return PassContent(
        name=entry_name,
        password=password,
        email=email,
        username=username,
        note=note
    )

def setup_gpg_agent_passphrase(passphrase: str):
    """
    Preset the passphrase in gpg-agent to avoid interactive prompts.
    This requires gpg-preset-passphrase to be available.
    """
    if not passphrase:
        return False

    try:
        encryption_keygrip = os.getenv("ENCRYPTION_KEYGRIP", "")
        success = True
        print(f"Setting passphrase for keygrip: {encryption_keygrip}")

        # Get cross-platform path to gpg-preset-passphrase
        try:
            gpgconf_result = subprocess.run(
                ["gpgconf", "--list-dirs", "libexecdir"],
                capture_output=True,
                text=True,
                check=True
            )
            libexec_dir = gpgconf_result.stdout.strip()
            preset_passphrase_path = os.path.join(libexec_dir, "gpg-preset-passphrase")
        except subprocess.CalledProcessError:
            # Fallback to common locations if gpgconf fails
            common_paths = [
                "/usr/local/bin/gpg-preset-passphrase",
                "/usr/bin/gpg-preset-passphrase",
                "/opt/homebrew/bin/gpg-preset-passphrase",
                "/usr/local/Cellar/gnupg/2.4.5_1/libexec/gpg-preset-passphrase"
            ]
            preset_passphrase_path = None
            for path in common_paths:
                if os.path.exists(path):
                    preset_passphrase_path = path
                    break

            if not preset_passphrase_path:
                print("Could not find gpg-preset-passphrase. "
                      "Please ensure GnuPG is properly installed.")
                return False

        preset_proc = subprocess.run(
            [preset_passphrase_path, "--preset", encryption_keygrip],
            input=passphrase,
            text=True,
            capture_output=True,
            check=False
        )

        if preset_proc.returncode != 0:
            print(f"Failed to preset passphrase for keygrip {encryption_keygrip}: "
                  f"{preset_proc.stderr}")
            success = False
        else:
            print(f"Successfully preset passphrase for keygrip {encryption_keygrip}")

        return success
    except subprocess.SubprocessError as e:
        print(f"Failed to setup GPG passphrase: {e}")
        return False

def read_pass(entry_name):
    """Read a password entry from the pass store."""
    env = os.environ.copy()
    env["GPG_TTY"] = subprocess.run(
        ["tty"], capture_output=True, text=True, check=False
    ).stdout.strip()

    try:
        result = subprocess.run(
            ["pass", entry_name],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,  # Add timeout to prevent hanging
            check=False
        )

        if result.returncode != 0:
            print(f"Error reading {entry_name}: {result.stderr}")
            return None

        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"Timeout reading {entry_name}")
        return None
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Exception reading {entry_name}: {e}")
        return None

def write_pass(output_file: str, rows: List[PassContent]):
    """Write password entries to CSV file for Proton Pass import."""
    # Expand user path and ensure directory exists
    expanded_output_file = os.path.expanduser(output_file)
    output_dir = os.path.dirname(expanded_output_file)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, mode=0o700)  # Secure permissions for password data
        print(f"Created output directory: {output_dir}")

    with open(expanded_output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PROTON_HEADERS)
        writer.writeheader()
        for r in rows:
            row_dict = asdict(r)
            row_dict['vault'] = None  # Add vault field as None
            writer.writerow(row_dict)


def setup_gpg_passphrase():
    """Setup GPG passphrase from environment or user input."""
    passphrase = os.getenv("GPG_PASSPHRASE")
    if not passphrase:
        passphrase = getpass.getpass("Enter GPG passphrase: ")

    if passphrase:
        print("Setting up GPG passphrase...")
        if setup_gpg_agent_passphrase(passphrase):
            print("GPG passphrase setup successful")
        else:
            print("GPG passphrase setup failed, you may need to enter it manually")


def count_gpg_files(pass_store_path: str) -> int:
    """Count total GPG files in the pass store."""
    total_files = 0
    for _, _, files in os.walk(pass_store_path):
        for file in files:
            if file.endswith(".gpg"):
                total_files += 1
    return total_files


def process_all_entries(pass_store_path: str) -> tuple[List[PassContent], int, int]:
    """Process all password entries and return results."""
    processed_pass_rows: List[PassContent] = []
    processed_files = 0
    total_files = count_gpg_files(pass_store_path)

    print(f"Found {total_files} password entries to process")

    for root, _, files in os.walk(pass_store_path):
        for file in files:
            if not file.endswith(".gpg"):
                continue

            path = os.path.join(root, file)
            entry_name = os.path.relpath(path, pass_store_path)[:-4]

            print(f"Processing: {entry_name}")
            raw_pass_content = read_pass(entry_name)

            if raw_pass_content:
                processed_pass_content = process_pass(entry_name, raw_pass_content)
                processed_pass_rows.append(processed_pass_content)
                processed_files += 1
            else:
                print(f"  Failed to read: {entry_name}")

    return processed_pass_rows, processed_files, total_files


def main():
    """Main function to process all pass entries and create CSV export."""
    setup_gpg_passphrase()

    pass_store_path = os.path.expanduser(PASS_STORE)

    print("\n" + "="*50)
    print("Processing all entries...")
    print("="*50)

    processed_pass_rows, processed_files, total_files = process_all_entries(pass_store_path)

    print(f"\nSuccessfully processed {processed_files}/{total_files} entries")

    if processed_pass_rows:
        write_pass(OUTPUT_FILE, processed_pass_rows)
        print(f"CSV file written to: {OUTPUT_FILE}")
        print(f"Total entries in CSV: {len(processed_pass_rows)}")
    else:
        print("No entries were processed successfully")

if __name__ == "__main__":
    main()
