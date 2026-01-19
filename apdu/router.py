from __future__ import annotations
from typing import Callable, Dict
from apdu.parser import Apdu
from apdu import status_words as sw
from card.context import CardContext
from card.handlers import handle_select, handle_read_binary, handle_read_record


# Type alias: a handler takes (ctx, apdu) and returns response bytes (data + SW)
Handler = Callable[[CardContext, Apdu], bytes]

# Minimal INS map (common ISO 7816-4 instructions used for USIM FS access)
INS_SELECT_FILE = 0xA4
INS_READ_BINARY = 0xB0
INS_READ_RECORD = 0xB2


_HANDLERS: Dict[int, Handler] = {
    INS_SELECT_FILE: handle_select,
    INS_READ_BINARY: handle_read_binary,
    INS_READ_RECORD: handle_read_record,
}


def dispatch(ctx: CardContext, apdu: Apdu) -> bytes:
    """
    Route an APDU to the correct handler using INS.

    Returns:
      - Handler response bytes: <optional data> + SW1SW2
      - Or 6D00 if INS unsupported

    """
    handler = _HANDLERS.get(apdu.ins)
    if handler is None:
        return sw.SW_INS_NOT_SUPPORTED
    return handler(ctx, apdu)
