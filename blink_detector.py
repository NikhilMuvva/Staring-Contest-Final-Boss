"""Deprecated launcher kept for compatibility.

New code should import :class:`BlinkInput` from ``blink_input`` directly.
"""

from blink_input import BlinkInput, main

__all__ = ["BlinkInput"]


if __name__ == "__main__":
    main()
