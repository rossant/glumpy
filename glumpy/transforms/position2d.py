# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
from glumpy import library
from . transform import Transform

class Position2D(Transform):

    def __init__(self, *args, **kwargs):
        code = library.get("transforms/position-2d.glsl")
        Transform.__init__(self, code, *args, **kwargs)
