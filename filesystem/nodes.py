from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# The core node types are MF(Master file), DF(Dedicated file) and EF(Elementary file)


@dataclass
class FileNode:
    fid: int
    name: str
    parent: Optional["DF"] = field(default=None, init=False) 
    def __post_init__(self) -> None:
        if not (0x0000 <= self.fid <= 0xFFFF):
            raise ValueError(f"fid out of range: {self.fid:#06x}")
    @property
    def fid_hex(self) -> str:
        return f"{self.fid:04X}"
    
#Moving from bottom and top of the tree and appending the 'fid'(File Identifier) and reversing it to store in a list.
    def path_fids(self) -> List[int]:
        fids: List[int] = []
        node: Optional["FileNode"] = self
        while node is not None:
            fids.append(node.fid)
            node = node.parent
        return list(reversed(fids))

#Moving from bottom and top of the tree and appending the 'fid'(File Identifier) and reversing it to return a string.
    def path_str(self) -> str:
        parts: List[str] = []
        node: Optional["FileNode"] = self
        while node is not None:
            parts.append(f"{node.name}({node.fid_hex})")
            node = node.parent
        return "/".join(reversed(parts))
    

@dataclass
class DF(FileNode):
    """
    The Dedicated File (DF) is a container. MF is also effectively a DF (root).
    We store the children keyed by their FID for fast lookup.
    """
    children: Dict[int, FileNode] = field(default_factory=dict)

    def add_child(self, node: FileNode) -> None:
        """
        Attach a child DF/EF under this DF.
        """
        if node.fid in self.children:
            existing = self.children[node.fid]
            raise ValueError(
                f"Duplicate FID {node.fid:#06x} under {self.path_str()} "
                f"(already used by {existing.name})"
            )
        node.parent = self
        self.children[node.fid] = node

    def get_child(self, fid: int) -> Optional[FileNode]:
        """Lookup for the direct children by using the FID """
        return self.children.get(fid)

    def find(self, fid: int) -> Optional[FileNode]:
        """
        Recursive search from this DF in the downward direction.
        This is useful when we want to "search anywhere under current DF/ADF".
        """
        if fid == self.fid:
            return self
        # check the direct childrens first
        if fid in self.children:
            return self.children[fid]
        # then search deeper only through DFs
        for child in self.children.values():
            if isinstance(child, DF):
                hit = child.find(fid)
                if hit is not None:
                    return hit
        return None


@dataclass
class MF(DF):
    """
    Master File (MF) is just a DF at the root.
    Typical MF FID is 0x3F00, but here we keep it configurable.
    """
    pass

# EF types (Transparent EF and Linear Fixed EF)

@dataclass
#This is the base class
class EF(FileNode):
    pass


@dataclass
class TransparentEF(EF):
    """
    Transparent EF = raw byte array.
    Accessed via READ BINARY (offset + length).
    """
    content: bytes = b""

    def read_binary(self, offset: int, length: int) -> bytes:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if length < 0:
            raise ValueError("length must be >= 0")
        end = offset + length
        if offset > len(self.content):
            raise IndexError("offset out of range") #This error will be translated to SW(Status word) as 6B00
        return self.content[offset:end]

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass
class LinearFixedEF(EF):
    """
    Linear Fixed EF = list of fixed-size records.
    Accessed via READ RECORD (record_number).
    record_number in APDU is 1-based (record 1 is the first).
    """
    record_len: int
    records: List[bytes] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.record_len <= 0:
            raise ValueError("record_len must be > 0")
        for r in self.records:
            if len(r) != self.record_len:
                raise ValueError(
                    f"Record length mismatch in {self.path_str()}: "
                    f"expected {self.record_len}, got {len(r)}"
                )

    def read_record(self, record_number: int) -> bytes:
        if record_number <= 0:
            raise IndexError("record_number must be >= 1 (APDU uses 1-based indexing)")
        idx = record_number - 1
        if idx >= len(self.records):
            raise IndexError("record not found")
        return self.records[idx]

    @property
    def record_count(self) -> int:
        return len(self.records)


