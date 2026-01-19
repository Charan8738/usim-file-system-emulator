from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Apdu:
    """
    Parsed APDU (ISO 7816-4 style, short-length only).

    Command APDU layout (short APDU):
      Header (always 4 bytes):
        CLA INS P1 P2 (This is Case 1)

      Then optionally:
        Le                           (Case 2)
        Lc Data                      (Case 3)
        Lc Data Le                   (Case 4)

    This parser supports ONLY "short" APDUs where:
      - Lc is 1 byte (0..255)
      - Le is 1 byte (0..255, where 0 often means 256 in some specs)

    We ignore extended length APDUs.
    """
    cla: int
    ins: int
    p1: int
    p2: int
    lc: int
    data: bytes
    le: Optional[int]  # None means Le not present

    @property
    def p1p2(self) -> int:
        """ Combine P1 and P2 into a 16-bit value for convenience."""
        return (self.p1 << 8) | self.p2

    @property
    def has_data(self) -> bool:
        return self.lc > 0

    @property
    def has_le(self) -> bool:
        return self.le is not None


class ApduParseError(ValueError):
    pass


def parse_apdu(raw: bytes) -> Apdu:
    """
    Parse raw command APDU bytes into an Apdu object.

    Supported cases:
      - Case 1: 4 bytes: CLA INS P1 P2
      - Case 2: 5 bytes: CLA INS P1 P2 Le
      - Case 3: 5+ bytes: CLA INS P1 P2 Lc Data
      - Case 4: 6+ bytes: CLA INS P1 P2 Lc Data Le

    Raises ApduParseError for Value errors in the APDUs.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw APDU must be bytes or bytearray")

    raw = bytes(raw)

    if len(raw) < 4:
        raise ApduParseError("APDU too short: need at least 4 header bytes")

    cla, ins, p1, p2 = raw[0], raw[1], raw[2], raw[3]

    # Case 1: header only
    if len(raw) == 4:
        return Apdu(cla=cla, ins=ins, p1=p1, p2=p2, lc=0, data=b"", le=None)

    # Case 2: header + Le
    if len(raw) == 5:
        le = raw[4]
        return Apdu(cla=cla, ins=ins, p1=p1, p2=p2, lc=0, data=b"", le=le)

    # len >= 6 -> could be Case 3 or Case 4
    lc = raw[4]
    data_start = 5
    data_end = data_start + lc

    if data_end > len(raw):
        # Lc claims more data than exists
        raise ApduParseError(
            f"APDU malformed: Lc={lc} but only {len(raw)-5} data bytes present"
        )

    data = raw[data_start:data_end]
    remaining = raw[data_end:]  # could be empty or [Le] or invalid

    # Case 3: exactly Lc bytes after header, no Le
    if len(remaining) == 0:
        return Apdu(cla=cla, ins=ins, p1=p1, p2=p2, lc=lc, data=data, le=None)

    # Case 4: one trailing byte = Le
    if len(remaining) == 1:
        le = remaining[0]
        return Apdu(cla=cla, ins=ins, p1=p1, p2=p2, lc=lc, data=data, le=le)

    # Anything else is malformed
    raise ApduParseError(
        f"APDU malformed: unexpected {len(remaining)} trailing bytes after data"
    )


# Utility useful for test/debug

def apdu_from_hex(hex_str: str) -> Apdu:
    """
    Convenience function for tests:
      apdu_from_hex("00A4000C023F00") -> Apdu(...)
    """
    hx = hex_str.replace(" ", "").replace("\n", "").strip()
    if len(hx) % 2 != 0:
        raise ApduParseError("Hex string length must be even")
    return parse_apdu(bytes.fromhex(hx))
