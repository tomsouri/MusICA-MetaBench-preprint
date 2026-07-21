#!/usr/bin/env python3
# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

"""
white_noise_generator.py

Generates three forms of white noise:
  1. A 1-minute WAV audio file of white noise (using numpy + scipy).
  2. A 500x340 PNG image of white noise (using numpy + Pillow).
  3. A nonsensical MusicXML file — "white noise" as invalid, schema-violating
     MusicXML that no renderer could interpret meaningfully.
"""

import random
import string
import struct
import numpy as np
from scipy.io import wavfile
from PIL import Image
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent


# ──────────────────────────────────────────────────────────────────────
# 1. WAV White Noise (numpy + scipy)
# ──────────────────────────────────────────────────────────────────────

def generate_wav(filename: str = "white_noise.wav",
                 duration_sec: float = 60.0,
                 sample_rate: int = 44100):
    """Generate a 1-minute 16-bit mono WAV of white noise."""
    num_samples = int(sample_rate * duration_sec)
    noise = np.random.randint(-32768, 32768, size=num_samples, dtype=np.int16)
    wavfile.write(filename, sample_rate, noise)
    print(f"[✓] WAV white noise → '{filename}' "
          f"({duration_sec}s, {sample_rate} Hz, 16-bit mono)")


# ──────────────────────────────────────────────────────────────────────
# 2. PNG White Noise Image (numpy + Pillow)
# ──────────────────────────────────────────────────────────────────────

def generate_png(filename: str = "white_noise.png",
                 width: int = 500,
                 height: int = 340):
    """Generate a 500x340 RGB white noise image."""
    noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(noise, mode="RGB")
    img.save(filename)
    print(f"[✓] PNG white noise → '{filename}' ({width}×{height})")


# ──────────────────────────────────────────────────────────────────────
# 3. MusicXML "White Noise" — Nonsensical / Schema-Violating
# ──────────────────────────────────────────────────────────────────────
#
# Philosophy: Audio white noise is sound no instrument intentionally
# makes. Image white noise is an image of nothing recognizable.
# Therefore MusicXML white noise should be a score that is
# *well-formed XML* but **schematically absurd** — containing
# invalid pitches, impossible durations, contradictory attributes,
# garbage dynamics, and random unicode, such that no music
# application could render it as meaningful notation.
# ──────────────────────────────────────────────────────────────────────

# --- Random garbage generators ---

_UNICODE_RANGES = [
    (0x0041, 0x024F),   # Latin
    (0x0400, 0x04FF),   # Cyrillic
    (0x4E00, 0x9FFF),   # CJK
    (0x1F300, 0x1F6FF), # Emoji / symbols
    (0x0370, 0x03FF),   # Greek
    (0x2200, 0x22FF),   # Mathematical operators
]


def _rand_unicode(length: int = None) -> str:
    if length is None:
        length = random.randint(1, 8)
    chars = []
    for _ in range(length):
        lo, hi = random.choice(_UNICODE_RANGES)
        cp = random.randint(lo, hi)
        try:
            chars.append(chr(cp))
        except (ValueError, OverflowError):
            chars.append("☐")
    return "".join(chars)


def _rand_garbage_str(min_len: int = 1, max_len: int = 12) -> str:
    kind = random.choice(["unicode", "ascii_junk", "numeric_nonsense"])
    if kind == "unicode":
        return _rand_unicode(random.randint(min_len, max_len))
    elif kind == "ascii_junk":
        return "".join(random.choices(
            string.ascii_letters + string.digits + string.punctuation,
            k=random.randint(min_len, max_len)
        ))
    else:
        return str(random.uniform(-9999, 9999))



def _rand_invalid_step() -> str:
    """Return an invalid pitch step (valid = A-G only)."""
    invalid = list("HIJKLMNOPQRSTUVWXYZ0123456789") + [
        "♯", "♭", "𝄞", "🎵", "Do", "Re", "Zz", "#", "∞", "π",
        _rand_unicode(2),
    ]
    return random.choice(invalid)


def _rand_invalid_octave() -> str:
    """Return an absurd octave value."""
    return random.choice([
        str(random.randint(-100, -1)),
        str(random.randint(10, 9999)),
        "3.14159",
        "-∞",
        "NaN",
        "π",
        "99.99",
        _rand_garbage_str(),
    ])


def _rand_invalid_duration() -> str:
    """Return an absurd duration value."""
    return random.choice([
        str(random.randint(-1000, -1)),
        "0",
        str(random.randint(100000, 99999999)),
        "0.001",
        "∞",
        "-1",
        _rand_garbage_str(),
    ])


def _rand_invalid_type() -> str:
    """Return a nonsense note type (valid: whole, half, quarter, etc.)."""
    return random.choice([
        "257th", "zeroth", "whole", "tripple", "brëve",
        "1024th", "negative-half", "∅", "🎶", "semidemihemi",
        "centisecond", _rand_unicode(4), "forty-second",
        "imaginary", "NaN-th", "½½½", "eleventeenth",
    ])


def _rand_invalid_dynamic() -> str:
    """Return a nonsense dynamic."""
    return random.choice([
        "fffff", "pppppppp", "mfffz", "𝆏𝆏𝆏", "loud",
        "SCREAMING", "🔇", "inaudible", "∞",
        "f" * random.randint(5, 20),
        "p" * random.randint(6, 15),
        _rand_unicode(3),
    ])


def _rand_invalid_alter() -> str:
    """Return an absurd alter value (valid: -2 to 2 typically)."""
    return random.choice([
        str(random.randint(3, 100)),
        str(random.randint(-100, -3)),
        "42",
        "-999",
        "π",
        "0.123456789",
        str(random.uniform(-50, 50)),
    ])


def generate_musicxml(filename: str = "white_noise.musicxml",
                      num_measures: int = 30):
    """
    Generate a well-formed but schematically nonsensical MusicXML file.
    Every element contains invalid, absurd, or impossible values.
    """

    score = Element("score-partwise", version="4.0")

    # -- Absurd work title --
    work = SubElement(score, "work")
    SubElement(work, "work-title").text = f"White Noise №{_rand_unicode(6)}"

    # -- Identification with garbage --
    ident = SubElement(score, "identification")
    SubElement(ident, "creator", type="composer").text = _rand_unicode(15)
    SubElement(ident, "creator", type="lyricist").text = "👻🤖💀 " + _rand_garbage_str()
    rights = SubElement(ident, "rights")
    rights.text = "© " + _rand_unicode(20)

    # -- Part list with nonsense --
    part_list = SubElement(score, "part-list")
    num_parts = random.randint(1, 4)
    part_ids = []
    for i in range(num_parts):
        pid = f"P{_rand_garbage_str()}"  # invalid part ID characters
        part_ids.append(pid)
        sp = SubElement(part_list, "score-part", id=pid)
        SubElement(sp, "part-name").text = _rand_unicode(10)
        # Invalid MIDI instrument
        midi = SubElement(sp, "midi-instrument", id=f"I-{_rand_garbage_str()}")
        SubElement(midi, "midi-channel").text = str(random.randint(-10, 999))
        SubElement(midi, "midi-program").text = str(random.randint(-50, 500))

    # -- Generate measures for each part --
    for pid in part_ids:
        part = SubElement(score, "part", id=pid)

        for m in range(1, num_measures + 1):
            # Randomly use an absurd measure number sometimes
            mnum = str(m) if random.random() < 0.5 else _rand_garbage_str()
            measure = SubElement(part, "measure", number=mnum)

            # ── Attributes (first measure, or randomly) ──
            if m == 1 or random.random() < 0.2:
                attrs = SubElement(measure, "attributes")
                SubElement(attrs, "divisions").text = random.choice([
                    "0", "-7", "3.14159", "999999", _rand_garbage_str()
                ])

                key = SubElement(attrs, "key")
                SubElement(key, "fifths").text = random.choice([
                    str(random.randint(-30, 30)), "∞", "NaN", "☃"
                ])
                SubElement(key, "mode").text = random.choice([
                    "supersonic", "mixotrygian", "🎸", "invalid",
                    _rand_unicode(5), "anti-dorian", "major-ish"
                ])

                time_el = SubElement(attrs, "time")
                SubElement(time_el, "beats").text = random.choice([
                    "0", "-3", "π", "13/8", "∞", str(random.randint(50, 999))
                ])
                SubElement(time_el, "beat-type").text = random.choice([
                    "0", "7", "13", "-4", "🥁", str(random.randint(100, 999))
                ])

                clef = SubElement(attrs, "clef")
                SubElement(clef, "sign").text = random.choice([
                    "Z", "🎼", "∅", "treble", _rand_unicode(2), "Ω"
                ])
                SubElement(clef, "line").text = random.choice([
                    "0", "-1", "99", "π", _rand_garbage_str()
                ])

            # ── Tempo direction with absurd values ──
            if m == 1 or random.random() < 0.15:
                direction = SubElement(measure, "direction", placement="above")
                dt = SubElement(direction, "direction-type")
                metro = SubElement(dt, "metronome")
                SubElement(metro, "beat-unit").text = _rand_invalid_type()
                SubElement(metro, "per-minute").text = random.choice([
                    "0", "-120", "999999", "∞", _rand_garbage_str()
                ])
                SubElement(direction, "sound",
                           tempo=str(random.uniform(-500, 100000)))

            # ── Fill with nonsensical notes ──
            num_notes = random.randint(2, 12)
            for _ in range(num_notes):
                note_el = SubElement(measure, "note")

                # ~20% chance of a rest (but with a pitch anyway — contradiction)
                is_contradictory_rest = random.random() < 0.2
                if is_contradictory_rest:
                    SubElement(note_el, "rest")

                # Always add a pitch (even on rests → contradiction)
                pitch_el = SubElement(note_el, "pitch")
                SubElement(pitch_el, "step").text = _rand_invalid_step()
                if random.random() < 0.6:
                    SubElement(pitch_el, "alter").text = _rand_invalid_alter()
                SubElement(pitch_el, "octave").text = _rand_invalid_octave()

                SubElement(note_el, "duration").text = _rand_invalid_duration()
                SubElement(note_el, "type").text = _rand_invalid_type()

                # Contradictory voice numbers
                SubElement(note_el, "voice").text = random.choice([
                    "0", "-3", _rand_garbage_str(), str(random.randint(50, 999))
                ])

                # Invalid stem direction
                SubElement(note_el, "stem").text = random.choice([
                    "sideways", "inward", "🔼", "none-ish",
                    _rand_unicode(3), "diagonal"
                ])

                # Random nonsense dynamics attached to notes
                if random.random() < 0.3:
                    direction = SubElement(measure, "direction",
                                           placement="below")
                    dt = SubElement(direction, "direction-type")
                    dynamics_el = SubElement(dt, "dynamics")
                    SubElement(dynamics_el, _rand_invalid_dynamic())

                # Garbage notations
                if random.random() < 0.35:
                    notations = SubElement(note_el, "notations")
                    artic = SubElement(notations, "articulations")
                    SubElement(artic, random.choice([
                        "super-staccato", "anti-accent", "🎯",
                        "reverse-mordent-trill", _rand_unicode(4),
                        "explosive", "whisper", "gargle",
                    ]))

                # Random beam with invalid values
                if random.random() < 0.25:
                    SubElement(note_el, "beam",
                               number=str(random.randint(-5, 50))
                    ).text = random.choice([
                        "begin-end", "neither", "🌈",
                        _rand_unicode(3), "backward-hook-loop"
                    ])

                # Random lyric with garbage
                if random.random() < 0.2:
                    lyric = SubElement(note_el, "lyric",
                                       number=str(random.randint(-10, 99)))
                    SubElement(lyric, "syllabic").text = random.choice([
                        "beginning-end", "🗣️", "anti-single",
                    ])
                    SubElement(lyric, "text").text = _rand_unicode(
                        random.randint(1, 15)
                    )

    indent(score, space="  ")

    tree = ElementTree(score)
    with open(filename, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<!DOCTYPE score-partwise PUBLIC '
                b'"-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
                b'"http://www.musicxml.org/dtds/partwise.dtd">\n')
        tree.write(f, xml_declaration=False, encoding="UTF-8")

    print(f"[✓] MusicXML white noise → '{filename}' "
          f"({num_measures} measures, {num_parts} parts, all nonsensical)")


# ──────────────────────────────────────────────────────────────────────
# 4. ABC Notation "White Noise" — Nonsensical Score
# ──────────────────────────────────────────────────────────────────────
#
# Valid ABC uses:
#   - Headers: X: (index), T: (title), M: (meter), L: (unit length),
#     K: (key), Q: (tempo), etc.
#   - Notes: A-G / a-g with optional ^ _ = (accidentals), octave marks
#     (' ,), and duration multipliers (2, /2, 3/4, etc.)
#   - Bar lines: | || |: :| [| |]
#   - Chords: [CEG], decorations: !ff!, grace notes: {abc}
#
# Our "white noise" ABC will:
#   - Use invalid header values (M:π/🎵, K:Zbb anti-locrian, Q:∞)
#   - Emit invalid note names (H, Q, Ψ, 🎶)
#   - Use impossible accidentals (^^^^, ____=^^)
#   - Generate absurd durations (notes like Z99/0, c-3/π)
#   - Produce broken bar lines, nested chords, unterminated repeats
#   - Sprinkle random Unicode throughout
#   - Contradict itself (multiple conflicting K: and M: mid-tune)
# ──────────────────────────────────────────────────────────────────────

def generate_abc(filename: str = "white_noise.abc",
                 num_lines: int = 60):
    """
    Generate a nonsensical ABC notation file — structurally reminiscent
    of ABC but containing invalid notes, impossible headers, garbage
    decorations, and contradictory directives throughout.
    """

    lines: list[str] = []

    # ── Header block ──
    # X: reference number — should be a positive integer
    lines.append(f"X:{random.choice(['-7', '0', 'π', '∞', '🎵', _rand_unicode(3)])}")

    # T: title — garbage
    lines.append(f"T:White Noise №{_rand_unicode(10)} — {_rand_garbage_str()}")

    # C: composer
    lines.append(f"C:{_rand_unicode(12)} & {_rand_garbage_str()}")

    # M: meter — should be like 4/4, 3/4, 6/8
    invalid_meters = [
        "π/🎵", "-3/0", "∞/∞", "13/37", "0/0", "999/-1",
        f"{_rand_unicode(2)}/{_rand_unicode(2)}",
        "4/4/4", "none", "√2/π",
    ]
    lines.append(f"M:{random.choice(invalid_meters)}")

    # L: default note length — should be like 1/8, 1/4
    invalid_lengths = [
        "0/0", "-1/8", "π/4", "∞", "1/0", "7/13",
        f"{_rand_unicode(1)}/{random.randint(-99, 0)}",
    ]
    lines.append(f"L:{random.choice(invalid_lengths)}")

    # Q: tempo — should be like 1/4=120
    invalid_tempos = [
        "1/4=-∞", "🎶=999999", "0/0=NaN", "π/π=π",
        f"1/4={_rand_garbage_str()}", "1/0=0",
        f"{_rand_unicode(3)}={random.randint(-500, 0)}",
    ]
    lines.append(f"Q:{random.choice(invalid_tempos)}")

    # K: key — should be like C, Dm, Emin, Amix, etc.
    invalid_keys = [
        "Zbb anti-locrian", "H#m supersonic", "🎸 mixotrygian",
        "Ωmaj7 anti-dorian", f"{_rand_unicode(3)} {_rand_garbage_str()}",
        "Qbb none", "∅ chromatic-ish", "π pentatonic-ish",
        "#♭#♭ hypo-mega-phrygian",
    ]
    lines.append(f"K:{random.choice(invalid_keys)}")

    # Some extra invalid/duplicate/contradictory headers
    num_extra_headers = random.randint(2, 6)
    bogus_header_fields = ["M", "L", "K", "Q", "R", "Z", "N", "H", "W"]
    for _ in range(num_extra_headers):
        field = random.choice(bogus_header_fields)
        lines.append(f"{field}:{_rand_garbage_str()}")

    lines.append("")  # blank line before body (ABC convention)

    # ── Invalid note generators ──

    VALID_NOTES = list("ABCDEFGabcdefg")
    INVALID_NOTES = list("HIJKLMNOPQRSTUVWXYZhijklmnopqrstuvwxyz")
    SYMBOLS = ["🎵", "🎶", "♯", "♭", "𝄞", "Ψ", "Ω", "∅", "π", "∞",
               "√", "Σ", "Δ", "θ", "☃", "🔥", "💀", "🤖"]

    def _rand_note() -> str:
        """Generate one nonsensical ABC 'note'."""
        parts = []

        # Accidentals: valid are ^, ^^, _, __, =
        # We generate absurd stacks
        if random.random() < 0.7:
            acc_chars = random.choices(["^", "_", "="], k=random.randint(1, 6))
            parts.append("".join(acc_chars))

        # Note name: mostly invalid
        if random.random() < 0.7:
            parts.append(random.choice(INVALID_NOTES + SYMBOLS))
        else:
            parts.append(random.choice(VALID_NOTES))  # occasionally valid

        # Octave modifiers: valid are ' and ,
        # We stack them absurdly or mix them (contradictory)
        if random.random() < 0.5:
            oct_chars = random.choices(["'", ","], k=random.randint(1, 8))
            parts.append("".join(oct_chars))

        # Duration: valid are like 2, /2, 3/2
        # We generate impossible ones
        if random.random() < 0.6:
            dur = random.choice([
                "0", "-3", "/0", "π", "99/0", "-1/π",
                f"{random.randint(-20, 0)}/{random.randint(-5, 0)}",
                f"{random.randint(100, 9999)}",
                "∞", f"/{_rand_unicode(1)}",
                "3.14", "√2",
            ])
            parts.append(dur)

        return "".join(parts)

    def _rand_decoration() -> str:
        """Generate a nonsensical ABC decoration (!...! syntax)."""
        invalid_decorations = [
            "!ffffffffff!", "!anti-pp!", "!🔊!", "!explode!",
            "!reverse-trill!", "!gargle!", "!∞!",
            f"!{_rand_unicode(4)}!", "!sfzzzzzz!", "!whisper-scream!",
            "!negative-fermata!", "!hyper-mordent!", "!💀!",
            f"!{_rand_garbage_str(2, 8)}!", "!none!", "!anti-crescendo!",
        ]
        return random.choice(invalid_decorations)

    def _rand_chord() -> str:
        """Generate a nonsensical chord bracket with invalid contents."""
        num = random.randint(1, 6)
        notes = [_rand_note() for _ in range(num)]
        inner = "".join(notes)
        # Sometimes don't close the bracket (broken syntax)
        if random.random() < 0.15:
            return "[" + inner  # unterminated!
        return "[" + inner + "]"

    def _rand_grace() -> str:
        """Generate nonsensical grace notes."""
        num = random.randint(1, 4)
        notes = [_rand_note() for _ in range(num)]
        inner = "".join(notes)
        if random.random() < 0.15:
            return "{" + inner  # unterminated!
        return "{" + inner + "}"

    def _rand_barline() -> str:
        """Generate a random (often invalid) barline."""
        barlines = [
            "|", "||", "|:", ":|", "[|", "|]",  # valid
            "|||", "|:::|", ":|:", "[[||]]",     # invalid
            "|🎵|", f"|{_rand_unicode(1)}|",
            ":||:", "|||:", ":|:|:", "[|||]",
            f"|{_rand_garbage_str(1, 3)}|",
        ]
        return random.choice(barlines)

    def _rand_inline_field() -> str:
        """Generate a nonsensical inline field [X:value]."""
        field = random.choice(["K", "M", "L", "Q", "V", "P"])
        value = _rand_garbage_str(2, 15)
        # Sometimes don't close bracket
        if random.random() < 0.1:
            return f"[{field}:{value}"
        return f"[{field}:{value}]"

    def _rand_comment() -> str:
        """Generate a comment line with garbage."""
        return f"% {_rand_unicode(random.randint(5, 30))}"

    # ── Body: generate lines of nonsensical notation ──

    for line_idx in range(num_lines):
        # Occasionally insert contradictory mid-tune headers
        if random.random() < 0.08:
            field = random.choice(["K", "M", "L", "Q"])
            lines.append(f"{field}:{_rand_garbage_str(3, 15)}")
            continue

        # Occasionally insert a garbage comment
        if random.random() < 0.06:
            lines.append(_rand_comment())
            continue

        # Build one line of "music"
        tokens: list[str] = []
        num_tokens = random.randint(8, 25)

        for _ in range(num_tokens):
            r = random.random()

            if r < 0.40:
                # Plain nonsensical note
                tokens.append(_rand_note())
            elif r < 0.55:
                # Nonsensical chord
                tokens.append(_rand_chord())
            elif r < 0.65:
                # Nonsensical grace notes
                tokens.append(_rand_grace())
            elif r < 0.75:
                # Decoration
                tokens.append(_rand_decoration())
            elif r < 0.82:
                # Barline (often invalid)
                tokens.append(_rand_barline())
            elif r < 0.88:
                # Inline field change (contradictory)
                tokens.append(_rand_inline_field())
            elif r < 0.93:
                # Tuplet with absurd ratio — valid is (3, (3:2:3, etc.
                p = random.choice([
                    "-1", "0", "π", "∞", "99",
                    f"{random.randint(-10, 0)}:{random.randint(-5, 0)}",
                ])
                tokens.append(f"({p}")
            else:
                # Raw unicode garbage between notes
                tokens.append(_rand_unicode(random.randint(1, 5)))

        # Join with spaces (ABC is whitespace-flexible)
        line_str = " ".join(tokens)

        # Occasionally append a line continuation (\) even when invalid
        if random.random() < 0.1:
            line_str += " \\"

        lines.append(line_str)

    # Final line: sometimes end abruptly without a final barline,
    # sometimes with an absurd one
    lines.append(random.choice([
        _rand_barline(),
        _rand_note() + _rand_note(),  # no barline at all
        f"|] {_rand_unicode(5)}",     # junk after final barline
        "",                            # just nothing
    ]))

    # ── Write out ──
    content = "\n".join(lines) + "\n"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    total_lines = len(lines)
    print(f"[✓] ABC white noise → '{filename}' "
          f"({total_lines} lines of nonsensical notation)")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating white noise in three formats...\n")
    tgt_datadir = "data/white_noise/"
    # Ensure target directory exists
    import os
    os.makedirs(tgt_datadir, exist_ok=True)

    generate_wav(filename=tgt_datadir + "audio.mastermix.wav")
    generate_png(filename=tgt_datadir + "visual.short.png")
    generate_musicxml(filename=tgt_datadir + "symbolic.musicxml")
    generate_abc(filename=tgt_datadir + "symbolic.abc.txt")
    print("\nDone! 🎛️")