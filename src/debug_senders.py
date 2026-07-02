"""
debug_senders.py

Quick diagnostic: prints the sender name + address (and attachment count)
for every email currently in the Inbox, so we can see exactly what
Outlook reports for the printer's emails and match settings.json to it.

Run with: python src/debug_senders.py
"""

import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

for item in inbox.Items:
    try:
        name = item.SenderName
        address = item.SenderEmailAddress
        attachment_count = item.Attachments.Count
        print(f"Name: {name!r} | Address: {address!r} | Attachments: {attachment_count}")
    except AttributeError:
        # Not a normal mail item (meeting invite, etc.) - skip it
        continue