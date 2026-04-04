#!/bin/bash
# adm-clawfiles.sh - Erstellt CSV-Übersicht aller Files in /home/iggy/
# Output: /home/iggy/.openclaw/adm-clawfiles.csv

OUTPUT="/home/iggy/.openclaw/adm-clawfiles.csv"

echo "pfad,dateiname,erweiterung,groesse_bytes,geaendert,typ" > "$OUTPUT"

find /home/iggy/ \
  -not -path "*/sessions/*" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  2>/dev/null | while read -r filepath; do

  if [ -f "$filepath" ]; then
    typ="file"
  elif [ -d "$filepath" ]; then
    typ="dir"
  else
    continue
  fi

  dateiname=$(basename "$filepath")
  erweiterung="${dateiname##*.}"
  if [ "$erweiterung" = "$dateiname" ]; then erweiterung=""; fi
  groesse=$(stat -c%s "$filepath" 2>/dev/null || echo "0")
  geaendert=$(stat -c%y "$filepath" 2>/dev/null | cut -d' ' -f1)
  pfad=$(dirname "$filepath")

  echo "\"$pfad\",\"$dateiname\",\"$erweiterung\",\"$groesse\",\"$geaendert\",\"$typ\"" >> "$OUTPUT"

done

echo "✅ Fertig! $(wc -l < $OUTPUT) Einträge in $OUTPUT"
