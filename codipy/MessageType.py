from enum import Enum


class MessageType(Enum):
    """
    @brief Message Types
    @author Michael Niebisch
    @bug No known bugs

	Class defining message types
    """
    HEARTBEAT = 1  # Heartbeat RLE message type
    DATA = 2  # Data message type
    BEACON = 3  # WLAN beacon message
    HEARTBEAT_BITMAP = 4  # Heartbeat Bitmap message
