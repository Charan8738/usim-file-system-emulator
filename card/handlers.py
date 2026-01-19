from __future__ import annotations
from typing import Optional
from apdu.parser import Apdu
from apdu import status_words as sw
from filesystem.nodes import DF, FileNode, TransparentEF, LinearFixedEF
from card.context import CardContext


# SELECT FILE (INS = 0xA4)

def handle_select(ctx: CardContext, apdu: Apdu) -> bytes:
    """
    We implement :
      - SELECT by FID when apdu.data == 2 bytes (e.g., 3F00, 7FFF, 6F07)

    We keep selection rules simple:
      - If selecting MF (3F00) -> reset_to_mf()
      - Else try to find under current DF first, then globally under MF
      - On success: ctx.select_node(node) and return 9000
      - On failure: 6A82
    """
    # In many SELECT commands, Data carries the file id or path.
    if apdu.lc == 0 or len(apdu.data) == 0:
        return sw.SW_WRONG_LENGTH

    # 2-byte FID selection
    if len(apdu.data) != 2:
        return sw.SW_FUNC_NOT_SUPPORTED

    fid = (apdu.data[0] << 8) | apdu.data[1]

    # MF selection convenience
    if fid == ctx.mf_root.fid:
        ctx.reset_to_mf()
        return sw.SW_SUCCESS

    # Prefer "relative" lookup first (under current DF), then global lookup.
    node: Optional[FileNode] = ctx.find_under_current_df(fid)
    if node is None:
        node = ctx.find_anywhere(fid)

    if node is None:
        return sw.SW_FILE_NOT_FOUND

    ctx.select_node(node)
    return sw.SW_SUCCESS


# READ BINARY (INS = 0xB0)

def handle_read_binary(ctx: CardContext, apdu: Apdu) -> bytes:
    """
    READ BINARY for Transparent EF.

    - Offset = P1P2 (16-bit)
    - Length = Le (1 byte). If Le == 0, some specs interpret as 256.
      We'll treat Le==0 as 256 for realism.

    Returns: <data> + 9000, or an error status word.
    """
    current = ctx.current_file

    if not isinstance(current, TransparentEF):
        # Command not allowed on current selected file type
        return sw.SW_COMMAND_NOT_ALLOWED

    if apdu.le is None:
        # For READ BINARY you normally need Le
        return sw.SW_WRONG_LENGTH

    offset = apdu.p1p2
    length = 256 if apdu.le == 0 else apdu.le

    try:
        data = current.read_binary(offset=offset, length=length)
    except IndexError:
        # offset out of range / wrong P1P2
        return sw.SW_WRONG_P1P2
    except ValueError:
        return sw.SW_WRONG_P1P2

    return data + sw.SW_SUCCESS


# READ RECORD (INS = 0xB2) 

def handle_read_record(ctx: CardContext, apdu: Apdu) -> bytes:
    """
    READ RECORD for Linear Fixed EF.

    - Record number = P1 (1-based)
    - P2 indicates the "record access mode". Here ABSOLUTE only is implemented ((P2 & 0x07) == 0x04)
      ISO 7816-4 uses the lower 3 bits of P2:
        0x04 = absolute
        0x02 = next
        0x03 = previous

    - Length:
        If Le is present, return up to Le bytes (usually equals record_len).
        If Le missing, we return full record_len (common in emulators or tests).
    """
    current = ctx.current_file

    if not isinstance(current, LinearFixedEF):
        return sw.SW_COMMAND_NOT_ALLOWED

    mode = apdu.p2 & 0x07
    if mode != 0x04:
        return sw.SW_FUNC_NOT_SUPPORTED

    record_number = apdu.p1
    if record_number == 0:
        # APDU uses 1-based indexing; 0 is invalid
        return sw.SW_WRONG_P1P2

    try:
        record = current.read_record(record_number)
    except IndexError:
        return sw.SW_RECORD_NOT_FOUND

    # Deciding how many bytes to return
    if apdu.le is None:
        data = record
    else:
        length = 256 if apdu.le == 0 else apdu.le
        data = record[:length]

    return data + sw.SW_SUCCESS
