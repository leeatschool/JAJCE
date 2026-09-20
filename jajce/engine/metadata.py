import io
import re
import struct
from xml.sax.saxutils import escape as xml_escape
from pathlib import Path
from typing import List, Optional, Tuple
import piexif

class MetadataManager:
    """
    Handles generation, parsing, and injection of EXIF and XMP metadata
    specifically tailored for JPEG XL (.jxl) containers and standard photo tags.
    """

    @staticmethod
    def generate_xmp_bytes(tags: List[str], description: str = "") -> bytes:
        """
        Generates standard UTF-8 encoded XMP XML containing tags across Dublin Core,
        IPTC Core, Lightroom, and Windows Photo schemas for maximum viewer compatibility.
        """
        cleaned_tags = [t.strip() for t in tags if t.strip()]
        tag_items = "\n".join([f"          <rdf:li>{xml_escape(t)}</rdf:li>" for t in cleaned_tags])
        tags_joined = xml_escape(", ".join(cleaned_tags))
        desc_escaped = xml_escape(description if description else ", ".join(cleaned_tags))

        xmp = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="JAJCE JPEG XL Converter">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:Iptc4xmpCore="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"
    xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
    xmlns:MicrosoftPhoto="http://ns.microsoft.com/photo/1.0/"
    xmlns:lr="http://ns.adobe.com/lightroom/1.0/">
   <dc:subject>
    <rdf:Bag>
{tag_items}
    </rdf:Bag>
   </dc:subject>
   <Iptc4xmpCore:Keywords>
    <rdf:Bag>
{tag_items}
    </rdf:Bag>
   </Iptc4xmpCore:Keywords>
   <pdf:Keywords>{tags_joined}</pdf:Keywords>
   <MicrosoftPhoto:LastKeywordXMP>
    <rdf:Bag>
{tag_items}
    </rdf:Bag>
   </MicrosoftPhoto:LastKeywordXMP>
   <MicrosoftPhoto:LastKeywordIPTC>
    <rdf:Bag>
{tag_items}
    </rdf:Bag>
   </MicrosoftPhoto:LastKeywordIPTC>
   <lr:hierarchicalSubject>
    <rdf:Bag>
{tag_items}
    </rdf:Bag>
   </lr:hierarchicalSubject>
   <dc:title>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{desc_escaped}</rdf:li>
    </rdf:Alt>
   </dc:title>
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{desc_escaped}</rdf:li>
    </rdf:Alt>
   </dc:description>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
        return xmp.encode("utf-8")

    @staticmethod
    def generate_exif_bytes(tags: List[str], description: str = "") -> bytes:
        """
        Generates raw TIFF EXIF payload containing XPKeywords (Windows Explorer Tags),
        XPTitle, XPSubject, XPComment, XPAuthor, ImageDescription, and UserComment.
        Strips the JPEG APP1 'Exif\\0\\0' marker to produce pure TIFF bytes.
        """
        cleaned_tags = [t.strip() for t in tags if t.strip()]
        tags_joined_semi = "; ".join(cleaned_tags)
        tags_joined_comma = ", ".join(cleaned_tags)
        desc_str = description if description else tags_joined_comma

        # XP tags are stored as UTF-16LE byte arrays with null-terminator
        xp_keywords_bytes = (tags_joined_semi + "\0").encode("utf-16le")
        xp_title_bytes = (tags_joined_comma + "\0").encode("utf-16le")
        xp_subject_bytes = (desc_str + "\0").encode("utf-16le")
        xp_comment_bytes = (desc_str + "\0").encode("utf-16le")
        xp_author_bytes = ("JAJCE / SmolVLM\0").encode("utf-16le")

        # UserComment header (8 bytes) + ASCII comment
        user_comment_bytes = b"ASCII\x00\x00\x00" + desc_str.encode("utf-8", errors="replace")

        zeroth_ifd = {
            piexif.ImageIFD.ImageDescription: desc_str.encode("utf-8", errors="replace"),
            piexif.ImageIFD.XPKeywords: list(xp_keywords_bytes),
            piexif.ImageIFD.XPTitle: list(xp_title_bytes),
            piexif.ImageIFD.XPSubject: list(xp_subject_bytes),
            piexif.ImageIFD.XPComment: list(xp_comment_bytes),
            piexif.ImageIFD.XPAuthor: list(xp_author_bytes),
            piexif.ImageIFD.Software: b"JAJCE Image Converter (JPEG XL)"
        }
        exif_ifd = {
            piexif.ExifIFD.UserComment: user_comment_bytes
        }

        exif_dict = {
            "0th": zeroth_ifd,
            "Exif": exif_ifd,
            "GPS": {},
            "Interop": {},
            "1st": {},
            "thumbnail": None
        }

        raw = piexif.dump(exif_dict)
        if raw.startswith(b"Exif\x00\x00"):
            return raw[6:]
        return raw

    @classmethod
    def read_tags_from_jxl(cls, jxl_path: str) -> List[str]:
        """
        Extracts tags/keywords from a JPEG XL file by inspecting xml or Exif boxes.
        """
        try:
            with open(jxl_path, "rb") as f:
                data = f.read()
        except Exception:
            return []

        tags = set()

        # Check for XMP in JXL container or raw bytes
        xmp_match = re.search(rb"<dc:subject>[\s\S]*?</dc:subject>", data)
        if xmp_match:
            chunk = xmp_match.group(0).decode("utf-8", errors="ignore")
            li_items = re.findall(r"<rdf:li>(.*?)</rdf:li>", chunk)
            for item in li_items:
                if item.strip():
                    tags.add(item.strip())

        # Also search for MicrosoftPhoto:LastKeywordXMP
        mp_match = re.search(rb"<MicrosoftPhoto:LastKeywordXMP>[\s\S]*?</MicrosoftPhoto:LastKeywordXMP>", data)
        if mp_match:
            chunk = mp_match.group(0).decode("utf-8", errors="ignore")
            li_items = re.findall(r"<rdf:li>(.*?)</rdf:li>", chunk)
            for item in li_items:
                if item.strip():
                    tags.add(item.strip())

        # Search for XPKeywords in Exif IFD
        if b"XPKeywords" in data:
            try:
                # Find occurrences of tags in utf-16
                pass
            except Exception:
                pass

        return sorted(list(tags))

    @classmethod
    def inject_metadata_to_jxl(cls, jxl_path: str, tags: List[str], description: str = "") -> bool:
        """
        Directly parses and updates/injects 'xml ' and 'Exif' boxes in a .jxl container.
        If the file is a naked codestream, wraps it into a container format.
        """
        try:
            p = Path(jxl_path)
            with open(p, "rb") as f:
                data = f.read()

            if not data:
                return False

            xmp_bytes = cls.generate_xmp_bytes(tags, description)
            exif_bytes = cls.generate_exif_bytes(tags, description)
            if exif_bytes.startswith(b"Exif\x00\x00"):
                exif_bytes = exif_bytes[6:]
            # In JXL container, Exif box payload starts with 4-byte offset (0x00000000)
            exif_payload = b"\x00\x00\x00\x00" + exif_bytes

            def make_box(box_type: bytes, payload: bytes) -> bytes:
                box_len = len(payload) + 8
                return struct.pack(">I", box_len) + box_type + payload

            jxl_sig = b"\x00\x00\x00\x0C\x4A\x58\x4C\x20\x0D\x0A\x87\x0A"
            jxl_ftyp = b"\x00\x00\x00\x14\x66\x74\x79\x70\x6A\x78\x6C\x20\x00\x00\x00\x00\x6A\x78\x6C\x20"

            exif_box = make_box(b"Exif", exif_payload)
            xml_box = make_box(b"xml ", xmp_bytes)

            if data.startswith(b"\xFF\x0A"):
                # Naked codestream: wrap into full container
                jxlc_box = make_box(b"jxlc", data)
                new_data = jxl_sig + jxl_ftyp + exif_box + xml_box + jxlc_box
                with open(p, "wb") as f:
                    f.write(new_data)
                return True

            if data.startswith(jxl_sig):
                # Existing container: parse boxes
                pos = 12
                boxes: List[Tuple[bytes, bytes]] = []
                while pos < len(data):
                    if pos + 8 > len(data):
                        break
                    box_len = struct.unpack(">I", data[pos:pos+4])[0]
                    box_type = data[pos+4:pos+8]
                    if box_len == 1:
                        if pos + 16 > len(data):
                            break
                        box_len = struct.unpack(">Q", data[pos+8:pos+16])[0]
                        payload = data[pos+16:pos+box_len]
                        pos += box_len
                    elif box_len == 0:
                        payload = data[pos+8:]
                        pos = len(data)
                    else:
                        payload = data[pos+8:pos+box_len]
                        pos += box_len

                    # Remove existing Exif and xml boxes to replace them cleanly
                    if box_type not in (b"Exif", b"xml "):
                        boxes.append((box_type, payload))

                out = bytearray(jxl_sig)
                meta_added = False

                for b_type, b_payload in boxes:
                    out.extend(make_box(b_type, b_payload))
                    # Insert metadata right after ftyp box
                    if b_type == b"ftyp" and not meta_added:
                        out.extend(exif_box)
                        out.extend(xml_box)
                        meta_added = True

                if not meta_added:
                    out.extend(exif_box)
                    out.extend(xml_box)

                with open(p, "wb") as f:
                    f.write(out)
                return True

            return False
        except Exception as e:
            print(f"Error injecting metadata: {e}")
            return False
