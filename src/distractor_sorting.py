# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.




def dummy_shuffle(distractors: list, row: dict, rng) -> list:
    """
    A dummy sorting method that simply shuffles the distractors randomly. This is used as a baseline to compare against
    more sophisticated sorting methods. It does not take into account the content of the distractors or the question.
    """

    # create a copy of the list to avoid modifying the original
    # import random

    distractors = distractors.copy()
    rng.shuffle(distractors)
    return distractors