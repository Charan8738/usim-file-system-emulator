from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from filesystem.nodes import MF, DF, FileNode

@dataclass
class CardContext:
    """
    Holds the *state* of the emulated USIM card across multiple APDUs.

    Why we use it ?
    - APDUs are independent request/response messages
    - but a card session is stateful (after SELECT, the "current file" changes)

    Minimal v1 state:
    - mf_root: the MF tree root
    - current_df: currently selected DF/ADF (used as a base for relative selects)
    - current_file: currently selected file (DF or EF)
    """

    mf_root: MF
    current_df: DF
    current_file: FileNode

    def __post_init__(self) -> None:
        # On startup, a real card is effectively "at MF".
        # So if the caller didn't initialize properly, enforce MF as default.
        
        if self.current_df is None:
            self.current_df = self.mf_root
        if self.current_file is None:
            self.current_file = self.mf_root

    @classmethod
    def from_mf(cls, mf_root: MF) -> "CardContext":
        """
        this is a convenience constructor: It start with MF selected.
        """
        return cls(mf_root=mf_root, current_df=mf_root, current_file=mf_root)


    # Selection helpers
    def select_node(self, node: FileNode) -> None:
        """
        Update selection state to the given node.

        Rules :
        - current_file becomes node
        - if node is a DF, it also becomes current_df
        - if node is an EF, current_df remains unchanged
        """
        self.current_file = node
        if isinstance(node, DF):
            self.current_df = node

    def reset_to_mf(self) -> None:
        """
        Select MF (root). Useful for tests and for SELECT by MF.
        """
        self.current_df = self.mf_root
        self.current_file = self.mf_root


    # Lookup helpers
    def find_anywhere(self, fid: int) -> Optional[FileNode]:
        """
        Find a node anywhere in the tree (MF recursive search).
        Useful for debugging/tests or for global selection logic.
        """
        return self.mf_root.find(fid)

    def find_under_current_df(self, fid: int) -> Optional[FileNode]:
        """
        Find a node under the current DF (recursive).
        This matches a common "relative selection" model.
        """
        return self.current_df.find(fid)
