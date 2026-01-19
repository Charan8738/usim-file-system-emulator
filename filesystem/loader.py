from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from .nodes import MF, DF, FileNode, TransparentEF, LinearFixedEF


def _parse_fid(value: Union[int, str]) -> int:
    """
    Accepts:
      - int: 0..0xFFFF
      - str: "3F00" or "0x3F00" (hex)
    And it returns int fid.
    """
    if isinstance(value, int):
        fid = value
    elif isinstance(value, str):
        s = value.strip().lower()
        if s.startswith("0x"):
            s = s[2:]
        fid = int(s, 16)
    else:
        raise TypeError(f"fid must be int or hex str, got {type(value)}")
    if not (0x0000 <= fid <= 0xFFFF):
        raise ValueError(f"fid out of range: {fid:#06x}")
    return fid


def _read_bytes_from_spec(node_spec: Dict[str, Any], base_dir: Path) -> bytes:
    """
    For TransparentEF content.
    Supported in JSON:
      - "content_file": "ef_imsi.bin"  (loaded from base_dir/content_file)
      - "content_hex":  "0891..."      (hex string)
      - (optional) "content_ascii": "Hello" (encoded as ASCII)

    Priority order: content_file > content_hex > content_ascii > empty
    """

    if "content_file" in node_spec:
        p = base_dir / node_spec["content_file"]
        return p.read_bytes()

    if "content_hex" in node_spec:
        hx = node_spec["content_hex"].replace(" ", "").replace("\n", "")
        if len(hx) % 2 != 0:
            raise ValueError("content_hex must have even length")
        return bytes.fromhex(hx)

    if "content_ascii" in node_spec:
        return node_spec["content_ascii"].encode("ascii", errors="strict")

    return b""


def _read_records_from_spec(node_spec: Dict[str, Any], base_dir: Path) -> List[bytes]:
    """
    For LinearFixedEF record content.

    Supported in JSON:
      - "records_hex": ["01020304", "AABBCCDD", ...]  # list of hex strings
      - "records_file": "ef_sms_records.bin"          # binary file containing concatenated records
      - "records_ascii": ["HELLO.....", "BYE......."] # each must match record_len

    Priority: records_hex > records_file > records_ascii > empty
    """
    record_len = int(node_spec["record_len"])

    if "records_hex" in node_spec:
        recs: List[bytes] = []
        for hx in node_spec["records_hex"]:
            b = bytes.fromhex(str(hx).replace(" ", ""))
            recs.append(b)
        return recs

    if "records_file" in node_spec:
        p = base_dir / node_spec["records_file"]
        blob = p.read_bytes()
        if len(blob) % record_len != 0:
            raise ValueError(
                f"records_file length {len(blob)} not multiple of record_len {record_len}"
            )
        return [blob[i:i + record_len] for i in range(0, len(blob), record_len)]

    if "records_ascii" in node_spec:
        recs = []
        for s in node_spec["records_ascii"]:
            b = str(s).encode("ascii", errors="strict")
            recs.append(b)
        return recs
    return []


# This is the main Loader

def load_profile(profile_path: Union[str, Path], data_dir: Optional[Union[str, Path]] = None) -> MF:

    profile_path = Path(profile_path)
    base_dir = Path(data_dir) if data_dir is not None else profile_path.parent

    spec = json.loads(profile_path.read_text(encoding="utf-8"))
    root = _build_node_tree(spec, base_dir)

    if not isinstance(root, MF):
        raise ValueError("profile root must be type MF")
    return root

def _build_node_tree(spec: Dict[str, Any], base_dir: Path) -> FileNode:
    """
    Recursively build nodes from JSON spec.
    """
    node_type = str(spec.get("type", "")).strip().upper()
    fid = _parse_fid(spec["fid"])
    name = str(spec.get("name", f"FID_{fid:04X}"))

    # DF-like nodes
    if node_type in {"MF", "DF", "ADF"}:
        if node_type == "MF":
            node: DF = MF(fid=fid, name=name)
        else:
            node = DF(fid=fid, name=name)

        for child_spec in spec.get("children", []):
            child = _build_node_tree(child_spec, base_dir)
            node.add_child(child)
        return node

    # Transparent EF
    if node_type in {"EF_TRANSPARENT", "TRANSPARENT_EF", "EF_T"}:
        content = _read_bytes_from_spec(spec, base_dir)
        return TransparentEF(fid=fid, name=name, content=content)

    # Linear Fixed EF
    if node_type in {"EF_LINEAR_FIXED", "LINEAR_FIXED_EF", "EF_LF"}:
        if "record_len" not in spec:
            raise ValueError(f"{name}({fid:04X}) missing 'record_len' for EF_LINEAR_FIXED")

        records = _read_records_from_spec(spec, base_dir)
        record_len = int(spec["record_len"])
        return LinearFixedEF(fid=fid, name=name, record_len=record_len, records=records)

    raise ValueError(f"Unknown node type '{node_type}' for {name}({fid:04X})")
