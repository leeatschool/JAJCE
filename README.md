# JAJCE — Just Another JPEG Conversion Engine

**JAJCE** is a high-performance bulk image converter designed to convert a wide variety of image formats into modern **JPEG XL (`.jxl`)** format. It includes native bitstream-reversible lossless JPEG transcoding, high-density fresh lossy re-encoding, and a toggleable AI vision auto-tagger powered by **SmolVLM-256M-Instruct** that writes detected objects directly into standard `.jxl` container metadata tags.

![Icon](assets/icon.png)

---

## 🌟 Key Features

1. **Extensive Format Support**:
   - Converts JPEG (`.jpg`, `.jpeg`, `.jfif`, `.jpe`), PNG (`.png`, `.apng`), WebP (`.webp`), GIF (`.gif`), BMP (`.bmp`, `.dib`), TIFF (`.tif`, `.tiff`), AVIF (`.avif`, `.avifs`), TGA (`.tga`), NetPBM (`.ppm`, `.pgm`, `.pnm`, `.pam`, `.pfm`), ICO (`.ico`, `.cur`), and QOI (`.qoi`).
2. **Lossless Transcoding (Reversible)**:
   - For JPEGs: Losslessly transcodes DCT coefficients directly from the JPEG stream without generational loss, reducing file size by ~20% to ~40% while preserving **100% bit-exact reversibility** back to the original JPEG byte-for-byte (`djxl output.jxl reconstructed.jpg`).
   - For other formats (PNG, WebP, etc.): Performs mathematically lossless JPEG XL modular compression.
3. **Lossy Re-Encoding ("Fresh" Compression)**:
   - Decompresses and re-encodes with fresh JPEG XL VarDCT compression for maximum compression ratios.
   - Configurable Butteraugli visual distance (0.1 to 15.0, where 1.0 = visually lossless).
   - Configurable encoder effort levels (1 to 9).
   - Optional progressive decoding pass (`-p`).
4. **SmolVLM-256M-Instruct AI Auto-Tagging**:
   - Built-in toggleable AI vision assistant.
   - Automatically identifies items, subjects, and objects in photos.
   - Saves detected tags into `.jxl` container metadata under:
     - **XMP Dublin Core**: `<dc:subject><rdf:Bag><rdf:li>tag</rdf:li></rdf:Bag></dc:subject>`
     - **IPTC Core**: `<Iptc4xmpCore:Keywords>`
     - **Windows Explorer / Photo Tags**: Exif `XPKeywords` and MicrosoftPhoto `LastKeywordXMP`.
   - Allows live preview and manual editing of tags per image.
5. **Modern PySide6 GUI**:
   - Batch drag-and-drop for files and nested directories.
   - Queue management with live compression ratios, file sizes, and status tracking.
   - Split preview drawer displaying image thumbnails and tag chips.
   - Threaded background worker keeping the UI smooth and responsive.
   - Real-time collapsible log drawer.

---

## 🚀 Installation & Download

### Windows Installer (Recommended)
Download the latest **`JAJCE-v1.1.1-Setup.exe`** from [GitHub Releases](https://github.com/leeatschool/JAJCE/releases).
- Modern guided setup installer with Start Menu and Desktop shortcuts.
- Fully standalone: bundled with Python runtime, PyTorch, Transformers vision engine, and `libjxl` binaries. No extra dependencies required!

### Portable Release
Download **`JAJCE-v1.1.1-windows-x64.zip`**, extract anywhere, and run `JAJCE.exe`.

### Running from Source
If running from source repository:
```bash
# Clone and install dependencies
git clone https://github.com/leeatschool/JAJCE.git
cd JAJCE
pip install -r requirements.txt

# Run GUI
python main.py
```

### Command Line Interface (CLI)
You can also use JAJCE from scripts or terminal:

```bash
# Lossless reversible transcoding (default)
python main.py photo.jpg -o ./converted/

# Lossy re-encoding at distance 1.2 and effort 7
python main.py *.png --mode lossy -d 1.2 -e 7

# Batch conversion with SmolVLM auto-tagging enabled
python main.py images/ --tag
```

---

## 📁 Project Structure

```
JAJCE/
├── main.py                  # CLI & GUI entry point
├── run_jajce.bat            # Windows 1-click launcher
├── bin/                     # Bundled libjxl binaries (cjxl, djxl, jxlinfo)
│   ├── cjxl.exe
│   ├── djxl.exe
│   └── jxlinfo.exe
├── assets/                  # Application icons
│   ├── icon.ico
│   └── icon.png
└── jajce/
    ├── app.py               # Application initializer & AppUserModelID
    ├── engine/
    │   ├── jxl_bin.py       # Binary locator & verification
    │   ├── converter.py     # Conversion pipeline & format normalization
    │   ├── metadata.py      # XMP & Exif tag generator & JXL container injector
    │   └── worker.py        # Background QThread for batch execution
    ├── ui/
    │   ├── main_window.py   # Main window layout & controls
    │   ├── queue_widget.py  # Drag & drop table widget
    │   ├── settings_widget.py# Mode & compression sliders
    │   ├── preview_widget.py# Side preview & tag chips
    │   └── styles.py        # Modern dark theme QSS
    └── vlm/
        └── tagger.py        # SmolVLM-256M-Instruct inference manager
```
