#!/usr/bin/env python3
"""Surgical Rheingold Tab Fix — PROD & DEV
Replaces Rheingold iframe with div+fetch approach in index.html
"""
import re
import sys

def patch_index_html(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    changes = 0

    # CHANGE 1: Replace iframe with div placeholder
    old_iframe = re.compile(r'<iframe[^>]*src="/rheingold"[^>]*></iframe>')
    new_div = '<div id="rheingold-frame" style="width:100%;height:calc(100vh-180px);overflow-y:auto;background:#0a0a0f"><span style="color:#64748b;padding:20px">Klicke auf den Rheingold-Tab um zu laden...</span></div>'
    if old_iframe.search(content):
        content = old_iframe.sub(new_div, content)
        print(f"  ✅ iframe → div in {filepath}")
        changes += 1
    else:
        print(f"  ⚠️  iframe nicht gefunden in {filepath}")

    # CHANGE 2: Add rheingold case to switchTab function
    # Find switchTab and add rheingold handler
    rheingold_handler = """
            // Load Rheingold tab content on click (iframe replacement)
            if (tab === 'rheingold') {
                var el = document.getElementById('rheingold-frame');
                if (el && !el.dataset.loaded) {
                    el.innerHTML = '<span style="color:#64748b;padding:20px">Lädt Rheingold...</span>';
                    fetch('/rheingold/content')
                        .then(function(r) { return r.text(); })
                        .then(function(html) {
                            el.innerHTML = html;
                            el.dataset.loaded = '1';
                        })
                        .catch(function(e) {
                            el.innerHTML = '<span style="color:#ef4444;padding:20px">Fehler beim Laden: ' + (e.message || String(e)) + '</span>';
                        });
                }
            }"""

    # Find switchTab function body - look for existing tab-specific handlers
    # Pattern: find "if (tab === 'logs')" and add after it
    if "tab === 'rheingold'" not in content:
        # Add after 'logs' handler or at end of switchTab function
        pattern = r"(if \(tab === 'logs'\) \{[^}]+\})"
        match = re.search(pattern, content)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + rheingold_handler + "\n" + content[insert_pos:]
            print(f"  ✅ switchTab rheingold handler added in {filepath}")
            changes += 1
        else:
            # Try finding the function closing brace and insert before it
            print(f"  ⚠️  Could not find 'logs' handler in switchTab")
    else:
        print(f"  ℹ️  rheingold handler already in {filepath}")

    with open(filepath, 'w') as f:
        f.write(content)

    return changes

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: patch_rheingold_tab.py <index.html path>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    changes = patch_index_html(filepath)
    print(f"Done. {changes} change(s) made.")
