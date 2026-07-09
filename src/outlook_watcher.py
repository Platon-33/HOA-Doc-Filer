"""
outlook_watcher.py

Connects to the Outlook desktop app (it must already be open) and looks
for new scan emails from the printer. For each one found, it saves the
PDF attachment(s) to a local 'downloads' folder, then moves the email
into a 'Processed' subfolder so it won't be picked up again.

Run this with: python src/outlook_watcher.py
"""

import json
import os
import win32com.client
import paths

# PidTagSenderSmtpAddress - reliably resolves the real SMTP address even
# for Exchange resource/device accounts (like a networked printer) where
# SenderEmailAddress instead returns an unusable internal identifier.
PR_SENDER_SMTP_ADDRESS = "http://schemas.microsoft.com/mapi/proptag/0x5D01001E"


def get_real_sender_address(item):
    """Return the real SMTP address for an email's sender. Falls back to
    SenderEmailAddress if the property lookup fails for some reason."""
    try:
        address = item.PropertyAccessor.GetProperty(PR_SENDER_SMTP_ADDRESS)
        if address:
            return address
    except Exception:
        pass
    return item.SenderEmailAddress


def load_settings():
    """Read config/settings.json so the printer address / folder names
    live in one editable place instead of being hardcoded here."""
    config_path = os.path.join(paths.get_base_dir(), "config", "settings.json")
    with open(config_path, "r") as f:
        return json.load(f)


def get_outlook_folder(namespace, folder_name):
    """Grab a top-level Outlook folder by name (e.g. 'Inbox')."""
    inbox_root = namespace.GetDefaultFolder(6)  # 6 = the Inbox
    if folder_name.lower() == "inbox":
        return inbox_root
    # Otherwise look for a folder with this name under the same parent as Inbox
    for folder in inbox_root.Parent.Folders:
        if folder.Name.lower() == folder_name.lower():
            return folder
    raise ValueError(f"Could not find Outlook folder named '{folder_name}'")


def get_or_create_subfolder(parent_folder, subfolder_name):
    """Find the 'Processed' subfolder, creating it if this is the first run."""
    for folder in parent_folder.Folders:
        if folder.Name.lower() == subfolder_name.lower():
            return folder
    return parent_folder.Folders.Add(subfolder_name)


def find_and_save_scans(settings):
    """Main logic: scan the watched folder for printer emails, save their
    PDF attachments, then move the email to the Processed folder."""

    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    watched_folder = get_outlook_folder(namespace, settings["outlook_folder"])
    processed_folder = get_or_create_subfolder(
        watched_folder, settings["processed_folder_name"]
    )

    download_dir = os.path.join(paths.get_base_dir(), settings["download_folder"]
    )
    os.makedirs(download_dir, exist_ok=True)

    printer_address = settings["printer_sender_email"].lower()

    saved_files = []

    # .Items gives every email in the folder. We loop over a copy of the
    # list (via list()) because moving an item while iterating the live
    # Outlook collection can skip items - a classic gotcha with this API.
    items = list(watched_folder.Items)

    for item in items:
        try:
            sender = (get_real_sender_address(item) or "").lower()
        except AttributeError:
            # Skip anything that isn't a normal mail item (meeting invites, etc.)
            continue

        if sender != printer_address:
            continue

        if item.Attachments.Count == 0:
            continue

        pdf_found = False
        for attachment in item.Attachments:
            if attachment.FileName.lower().endswith(".pdf"):
                save_path = os.path.join(download_dir, attachment.FileName)
                # Avoid overwriting if two scans land with the same name
                save_path = _make_unique_path(save_path)
                attachment.SaveAsFile(save_path)
                saved_files.append(save_path)
                pdf_found = True

        if pdf_found:
            item.Move(processed_folder)

    return saved_files


def _make_unique_path(path):
    """If 'scan001.pdf' already exists, try 'scan001 (1).pdf', etc."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = f"{base} ({counter}){ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


if __name__ == "__main__":
    settings = load_settings()
    saved = find_and_save_scans(settings)
    if saved:
        print(f"Saved {len(saved)} new PDF(s):")
        for path in saved:
            print(f"  - {path}")
    else:
        print("No new scan emails found.")