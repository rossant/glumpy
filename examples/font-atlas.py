#! /usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
import numpy as np
from glumpy import app, gl, gloo, glm, text, data
from glumpy.log import log


vertex = """
    attribute vec2 position;
    attribute vec2 texcoord;
    varying vec2 v_texcoord;
    void main()
    {
        gl_Position = vec4(position, 0.0, 1.0);
        v_texcoord = texcoord;
    }
"""

fragment = """
    uniform sampler2D texture;
    varying vec2 v_texcoord;
    void main()
    {
        gl_FragColor = texture2D(texture, v_texcoord);
    }
"""

window = app.Window(width=512, height=512)

@window.event
def on_draw(dt):
    window.clear()
    program.draw(gl.GL_TRIANGLE_STRIP)

program = gloo.Program(vertex, fragment, count=4)
program['position'] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
program['texcoord'] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]
log.info("Caching texture fonts")

for size in range(8,25):
    font = text.TextureFont(data.get("OpenSans-Regular.ttf"), size)
    font.load(""" !\"#$%&'()*+,-./0123456789:;<=>?"""
              """@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"""
              """`abcdefghijklmnopqrstuvwxyz{|}~""")
program['texture'] = font.atlas

app.run()
