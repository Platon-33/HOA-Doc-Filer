# HOA Doc Filer

Semi-automated tool to pull scanned PDFs from printer emails in Outlook,
suggest a file name and folder based on the document's content, and file
them into the correct local workspace folder for SharePoint sync.

## Status
🚧 Work in progress. Building piece by piece.

## Project layout
```
hoa-doc-filer/
├── config/
│   ├── properties.json   # list of HOA clients + name variations
│   └── doc_types.json    # list of document categories + keywords
├── src/                  # the actual scripts (coming soon)
├── logs/                 # run logs (not committed)
├── requirements.txt
└── README.md
```

## Setup (Windows)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Config
- Edit `config/properties.json` to add new HOA clients as they come on board.
- Edit `config/doc_types.json` to add/tune document categories and keywords.
