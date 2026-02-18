import importlib.util
import os
import sysconfig

_stdlib_enum_path = os.path.join(sysconfig.get_path("stdlib"), "enum.py")
_stdlib_enum_spec = importlib.util.spec_from_file_location("_stdlib_enum", _stdlib_enum_path)
_stdlib_enum = importlib.util.module_from_spec(_stdlib_enum_spec)
_stdlib_enum_spec.loader.exec_module(_stdlib_enum)

# Re-export stdlib enum symbols so this module remains compatible with imports
# such as `from enum import IntFlag`.
for _name in dir(_stdlib_enum):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_stdlib_enum, _name)

class Suit(Enum):
    HEARTS = 'Hearts'
    DIAMONDS = 'Diamonds'
    CLUBS = 'Clubs'
    SPADES = 'Spades'

class Rank(Enum):
    TWO = '2'
    THREE = '3'
    FOUR = '4'
    FIVE = '5'
    SIX = '6'
    SEVEN = '7'
    EIGHT = '8'
    NINE = '9'
    TEN = '10'
    JACK = 'J'
    QUEEN = 'Q'
    KING = 'K'
    ACE = 'A'
