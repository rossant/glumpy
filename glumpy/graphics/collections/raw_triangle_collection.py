# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
import numpy as np
from glumpy import gl, library
from glumpy.transforms import Position3D
from . collection import Collection


class RawTriangleCollection(Collection):
    """
    """

    def __init__(self, user_dtype=None, transform=None,
                 vertex = None, fragment = None, **kwargs):

        base_dtype = [('position', (np.float32, 3), '!local', (0,0,0)),
                      ('color',    (np.float32, 4), 'local', (0,0,0,1)) ]

        dtype = base_dtype
        if user_dtype:
            dtype.extend(user_dtype)

        if vertex is None:
            vertex = library.get('collections/raw-triangle.vert')
        if fragment is None:
            fragment = library.get('collections/raw-triangle.frag')

        Collection.__init__(self, dtype=dtype, itype=np.uint32, mode=gl.GL_TRIANGLES,
                            vertex=vertex, fragment=fragment, **kwargs)

        # Set hooks if necessary
        if "transform" in self._program._hooks.keys():
            if transform is not None:
                self._program["transform"] = transform
            else:
                self._program["transform"] = Position3D()



    def append(self, points, indices, **kwargs):
        """
        Append a new set of vertices to the collection.

        For kwargs argument, n is the number of vertices (local) or the number
        of item (shared)

        Parameters
        ----------

        points : np.array
            Vertices composing the triangles

        indices : np.array
            Indices describing triangles

        color : list, array or 4-tuple
           Path color
        """

        itemsize  = len(points)
        itemcount = 1

        V = np.empty(itemcount*itemsize, dtype=self.vtype)
        for name in self.vtype.names:
            if name not in ['collection_index', 'position']:
                V[name] = kwargs.get(name, self._defaults[name])
        V["position"] = points

        # Uniforms
        if self.utype:
            U = np.zeros(itemcount, dtype=self.utype)
            for name in self.utype.names:
                if name not in ["__unused__"]:
                    U[name] = kwargs.get(name, self._defaults[name])
        else:
            U = None

        I = np.array(indices).ravel()

        Collection.append(self, vertices=V, uniforms=U, indices=I,
                                itemsize=itemsize)
