#!/usr/bin/env python3
"""Find all PDFs and write list to file."""
import os

pdfs = []
for root, dirs, files in os.walk("/home/iggy/.openclaw/rheingold_data/"):
    for f in files:
        if f.lower().endswith('.pdf'):
            pdfs.append(os.path.join(root, f))

pdfs.sort()
with open("/tmp/pdf_list.txt", "w") as f:
    for p in pdfs:
        f.write(p + "\n")

print(f"Found {len(pdfs)} PDFs")
