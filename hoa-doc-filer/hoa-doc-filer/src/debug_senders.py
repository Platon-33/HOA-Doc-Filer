"""
debug_senders.py

Quick diagnostic: tries multiple methods to resolve the real SMTP
address behind an Exchange sender, since not every method works for
every kind of Exchange account (regular mailbox vs. resource/device
account like a networked printer).

Run with: python src/debug_senders.py
"""

import win32com.client

# PidTagSenderSmtpAddress - the correct tag for a mail item's sender SMTP
PR_SENDER_SMTP_ADDRESS = "http://schemas.microsoft.com/mapi/proptag/0x5D01001E"


def try_property_accessor(item):
    try:
        return item.PropertyAccessor.GetProperty(PR_SENDER_SMTP_ADDRESS)
    except Exception as e:
        return f"(failed: {e})"


def try_exchange_user(item):
    try:
        exchange_user = item.Sender.GetExchangeUser()
        if exchange_user:
            return exchange_user.PrimarySmtpAddress
        return "(GetExchangeUser returned None - not a full mailbox)"
    except Exception as e:
        return f"(failed: {e})"


outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

for item in inbox.Items:
    try:
        name = item.SenderName
        attachment_count = item.Attachments.Count
        print(f"Name: {name!r}  (Attachments: {attachment_count})")
        print(f"  Method 1 (PropertyAccessor):  {try_property_accessor(item)}")
        print(f"  Method 2 (GetExchangeUser):   {try_exchange_user(item)}")
        print()
    except AttributeError:
        continue