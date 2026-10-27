"""BRUH"""

import numpy as np
import math

import inspect
import sys
import traceback

from typing import Callable, Any


def bits(value: int, width: int = 8) -> str:
    return f"{value:0{width}b}"


chars = [
    # Valid (10)
    "a",
    "Z",
    " ",
    "~",
    "0",
    "\n",
    "\t",
    "!",
    "?",
    "}",
    # Invalid (10)
    "\x00",
    "\x1f",
    "\x7f",
    "\x80",
    "é",
    "\r",
    "\x0b",
    "\x07",
    "€",
    "😀",
]


class Mixer:
    """Produces a reversible 2**<bits_down> : 1 mapping."""

    def __init__(self, width: int = 16, bits_down: int = 4):
        self.width = width
        self.bits_down = bits_down
        self.mask = (1 << self.width) - 1
        self.mult = 0x9E37
        self.inverse = pow(self.mult, -1, 1 << self.width)

    def _mix(self, value: int) -> int:
        return (value * self.mult) & self.mask

    def _unmix(self, value: int) -> int:
        return (value * self.inverse) & self.mask

    def map_down(self, value: int) -> int:
        """assumes un-mapped-down value input."""
        return self._mix(value) >> self.bits_down

    def map_up(self, value: int) -> list[int]:
        """assumes mapped-down value input. produces ambiguous list."""

        prepared = value << self.bits_down
        out = []
        for i in range(2**self.bits_down):
            out.append(self._unmix(prepared | i))
        return out


class ValidatorException(Exception):
    """There was an exception validating the candidate."""


class Validator:
    def __init__(self, method: Callable[[int, int], int]):
        self.method = method
        self.io: list[tuple[int, bool]] = []
        self._generate_io()

    def _generate_io(self):
        for v in chars:
            self.io.append((v, self.method(v)))
        print(self.io)

    def _compile_canditate(self, candidate: str):
        namespace = {}
        try:
            # too broad but good for POC
            exec(candidate, namespace)
        except Exception as e:
            raise ValidatorException("exec failed") from e

        last_key = next(reversed(namespace))
        last_value = namespace[last_key]

        if not isinstance(last_value, Callable):
            raise ValidatorException("Not Callable")

        return last_value

    def check(self, candidate: str, show_reason: bool = False) -> bool:
        """Returns True if the candidate compiles and passes the io harness"""
        try:
            self._compile_canditate(candidate)
        except ValidatorException as e:
            if show_reason:
                traceback.print_exc(e)

            return False

        return True


def valid_char(char: str) -> bool:
    return char in "\n\t" or 32 <= ord(char) <= 126


def calculate_ambiguity(options: list[list[str]]) -> tuple[int, float]:

    counts = [len(options) for options in options]

    total_candidates = math.prod(counts)
    ambiguity_bits = sum(math.log2(count) for count in counts)
    return total_candidates, ambiguity_bits


if __name__ == "__main__":

    # ------------------------------------------------ Setup

    data: str = inspect.getsource(sys.modules[__name__].valid_char)
    val = Validator(valid_char)

    print(data)
    print("Length: ", len(data))

    data_bits = 8
    index_bits = (len(data) - 1).bit_length()

    width = data_bits + index_bits
    bits_down = 12

    print(data_bits, index_bits, width, bits_down)

    # ------------------------------------------------- Mix
    print("-" * 100, "Mix")

    m = Mixer(width, bits_down=bits_down)

    collisions = set()
    combineds = []
    m_downs = []
    for i, d in enumerate(data.encode()):

        mask = i << 8
        combined = mask | d
        combineds.append(combined)

        m_down = m.map_down(combined)
        collisions.add(m_down)

        if m_down in m_downs:
            print("collision")
            collisions.add(combined)

        m_downs.append(m_down)

        print(f"{chr(d):<4}{d:<5} {bits(d)} {bits(combined, 14)}, {bits(m_down, 6)}")

    # ------------------------------------------------- unmix

    print("-" * 100, "Unmix")

    hits: dict[int, list[int]] = {i: [] for i in range(len(m_downs))}

    for i, mapped in enumerate(m_downs):
        for v in m.map_up(mapped):
            if (v >> data_bits) == i:
                hits[i].append(v)
        print(data[i].__repr__(), mapped, combineds[i], hits[i])

    options = [
        [chr(v & 0xFF) for v in hits[i] if valid_char(chr(v & 0xFF))]
        for i in range(len(hits))
    ]

    for i, o in enumerate(options):
        print(o)

    cand, amb = calculate_ambiguity(options)
    print(f"Canditates: {cand:,}, Ambiguity Bits: {amb:.2f}")

    print(val.io)
