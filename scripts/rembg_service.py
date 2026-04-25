#!/usr/bin/env python3
"""
SIAS Image Tools — rembg Background Removal + 4x Upscale Service
Läuft auf Port 5050 (separater Microservice, wird vom Dashboard Tab eingebunden)
"""

import io
import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
from rembg import remove

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sias-imgtools")

app = Flask(__name__)
CORS(app)  # Dashboard DEV (5001) darf drauf zugreifen

MAX_UPLOAD_BYTES = 30 * 1024 * 1024   # 30 MB Input-Limit
MAX_OUTPUT_BYTES =  8 * 1024 * 1024   # 8 MB Output-Limit
UPSCALE_FACTOR   = 4
ALLOWED_TYPES    = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def enforce_size_limit(img: Image.Image, max_bytes: int) -> Image.Image:
    """PNG-Kompression iterativ erhöhen bis unter max_bytes."""
    for compress in range(1, 10):
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True, compress_level=compress)
        if buf.tell() <= max_bytes:
            buf.seek(0)
            return buf
    # Letzter Ausweg: leicht downscalen
    factor = 0.95
    work = img.copy()
    for _ in range(20):
        buf = io.BytesIO()
        work.save(buf, format="PNG", optimize=True, compress_level=9)
        if buf.tell() <= max_bytes:
            buf.seek(0)
            return buf
        w, h = work.size
        work = work.resize((int(w * factor), int(h * factor)), Image.LANCZOS)
    buf.seek(0)
    return buf


@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "sias-imgtools", "version": "1.0"})


@app.route("/remove-bg", methods=["POST"])
def remove_bg():
    """
    POST /remove-bg
    Form-Data: file = <image>
    Returns: PNG mit transparentem Hintergrund
    """
    if "file" not in request.files:
        return jsonify({"error": "Kein File-Feld im Request"}), 400

    f = request.files["file"]
    if f.content_type not in ALLOWED_TYPES:
        return jsonify({"error": f"Dateityp nicht unterstützt: {f.content_type}"}), 400

    raw = f.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Datei zu groß (max 30 MB)"}), 413

    logger.info(f"remove-bg: {f.filename} ({len(raw)//1024} KB)")

    try:
        result_bytes = remove(raw)  # rembg gibt RGBA PNG zurück
        img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        out = enforce_size_limit(img, MAX_OUTPUT_BYTES)
        return send_file(
            out,
            mimetype="image/png",
            as_attachment=False,
            download_name="no-bg.png"
        )
    except Exception as e:
        logger.exception("remove-bg failed")
        return jsonify({"error": str(e)}), 500


@app.route("/upscale", methods=["POST"])
def upscale():
    """
    POST /upscale
    Form-Data: file = <PNG mit Transparenz>
    Returns: PNG 4x Größe, max 8 MB
    """
    if "file" not in request.files:
        return jsonify({"error": "Kein File-Feld im Request"}), 400

    f = request.files["file"]
    raw = f.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Datei zu groß (max 30 MB)"}), 413

    logger.info(f"upscale: {f.filename} ({len(raw)//1024} KB)")

    try:
        img = Image.open(io.BytesIO(raw))
        mode = img.mode  # RGBA behalten
        w, h = img.size
        new_w, new_h = w * UPSCALE_FACTOR, h * UPSCALE_FACTOR

        logger.info(f"upscale: {w}x{h} → {new_w}x{new_h}")
        big = img.resize((new_w, new_h), Image.LANCZOS)

        out = enforce_size_limit(big, MAX_OUTPUT_BYTES)
        return send_file(
            out,
            mimetype="image/png",
            as_attachment=False,
            download_name="upscaled-4x.png"
        )
    except Exception as e:
        logger.exception("upscale failed")
        return jsonify({"error": str(e)}), 500


@app.route("/remove-bg-upscale", methods=["POST"])
def remove_bg_and_upscale():
    """
    POST /remove-bg-upscale
    Kombiniert: Hintergrund entfernen + 4x Upscale in einem Schritt
    Form-Data: file = <image>
    Returns: PNG RGBA 4x, max 8 MB
    """
    if "file" not in request.files:
        return jsonify({"error": "Kein File-Feld im Request"}), 400

    f = request.files["file"]
    raw = f.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Datei zu groß (max 30 MB)"}), 413

    logger.info(f"remove-bg-upscale: {f.filename} ({len(raw)//1024} KB)")

    try:
        # Schritt 1: Background entfernen
        result_bytes = remove(raw)
        img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        # Schritt 2: 4x Upscale
        w, h = img.size
        big = img.resize((w * UPSCALE_FACTOR, h * UPSCALE_FACTOR), Image.LANCZOS)

        out = enforce_size_limit(big, MAX_OUTPUT_BYTES)
        return send_file(
            out,
            mimetype="image/png",
            as_attachment=False,
            download_name="no-bg-4x.png"
        )
    except Exception as e:
        logger.exception("remove-bg-upscale failed")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    logger.info("SIAS Image Tools Service startet auf Port 5050...")
    app.run(host="192.168.23.80", port=5050, debug=False, threaded=True)
