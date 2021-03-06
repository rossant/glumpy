# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nicolas P. Rougier
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
from . window import event
from glumpy.log import log
from glumpy import gloo, transforms, library



class Viewport(event.EventDispatcher):
    """
    A Viewport represents a rectangular area on a window. It can has children
    whose size can be defined in absolute coordinates or in relative
    coordinates relatively to the parent viewport. Let's consider a root
    viewport of size 400x400 and a child viewport:

    child.size = 100,100
    -> Final size will be 100,100

    child.size = -100,-100
    -> Final size will be (400-100),(400-100) = 300,300

    child.size = 0.5,0.5
    -> Final size will be (.5*400),(.5*400) = 200,200

    child.size = -0.5,-0.5
    -> Final size will be (400*(1-0.5)),(400*(1-0.5)) = 200,200

    Note that it is also possible to define an aspect (=height/width) that can
    be enforced. Positioning the viewport inside the parent viewport is also
    made using absolute or relative coordinates. Let's consider again the root
    viewport whose default coordinates are always +0+0:

    child.position = +10,+10
    -> Final position will be +10+10

    child.position = -10,-10
    -> Final position will be (400-10,400-10) = 390,390

    child.position = 0.25,0.25
    -> Final position will be (400*0.25,400*0.25) = 100,100

    child.position = -0.25,-0.25
    -> Final position will be (400*(1-0.25),400*(1-0.25) = 300,300

    Note that the final position of the viewport relates to the anchor point
    which can be also set in absolute or relative coordinates.

    The order of rendering is done according to the order of the viewport
    hierarchy, starting from the root viewport.

    Any child viewport is guaranteed to be clipped against the parent viewport.
    """


    # Internal id counter to keep track of created objects
    _idcount = 0


    def __init__(self, size=(800,600), position=(0,0), anchor=(0,0), aspect=None):
        """
        Create a new viewport with requested size and position.

        Parameters
        ----------
        size: tuple as ([int,float], [int,float])
            Requested size.
            May be absolute (pixel) or relative to the parent (percent).
            Positive or negative values are accepted.

        position: tuple as ([int,float], [int,float])
            Requested position.
            May be absolute (pixel) or relative to the parent (percent).
            Positive or negative values are accepted.

        anchor: tuple as ([int,float], [int,float]) or string
            Anchor point for positioning.
            May be absolute (pixel) or relative (percent).
            Positive or negative values are accepted.

        aspect: float
            Aspect (width/height) to be enforced.
        """

        self._parent = None
        self._children = []
        self._active_viewports = []

        # Aspect ratio (width/height)
        self._aspect = aspect
        if aspect:
            log.info("Enforcing %.1f aspect ratio" % aspect)

        # Anchor point for placement
        self._anchor = anchor

        # Requested size & position (may be honored or not, depending on parent)
        # (relative or absolute coordinates)
        self._requested_size     = size
        self._requested_position = position

        # Clipped size & position (used for glScissor)
        # (absolute coordinates)
        self._scissor_size     = size
        self._scissor_position = position

        # Viewport size & position (used for glViewport)
        # (absolute coordinates)
        self._viewport_size     = size
        self._viewport_position = position

        # Wheter viewport is active (cursor is inside)
        self._active = False

        # Viewport id
        self._id = Viewport._idcount
        Viewport._idcount += 1

        self._clipping = transforms.Transform(library.get("viewport-clipping.glsl"))
        self._transform = transforms.Transform(library.get("viewport-transform.glsl"))


    def add(self, child):
        """ Add a new child to the viewport """

        child._parent = self
        self._children.append(child)


    def __getitem__(self, index):
        """Get children using index"""

        return self._children[index]


    @property
    def transform(self):
        """ Transform snippet """

        return self._transform


    @property
    def clipping(self):
        """ Clipping snippet """

        return self._clipping


    @property
    def name(self):
        """ Viewport name """

        return "VP%d" % (self._id)


    @property
    def active(self):
        """ Whether viewport is active """

        return self._active

    @active.setter
    def active(self, value):
        """ Whether viewport is active """

        self._active = value
        for child in self._children:
            child.active = value


    @property
    def root(self):
        """ Root viewport """

        if not self._parent:
            return self
        return self._parent

    @property
    def parent(self):
        """ Parent viewport """
        return self._parent


    @property
    def viewport(self):
        """ Actual position and size of the viewport """

        x,y = self._viewport_position
        w,h = self._viewport_size
        return x, y, w, h


    @property
    def size(self):
        """ Actual size of the viewport """

        return self._viewport_size

    @size.setter
    def size(self, size):
        """ Actual size of the viewport """

        self._requested_size = size
        self.root._compute_viewport()


    @property
    def position(self):
        """ Actual position of the viewport """

        return self._viewport_position


    @position.setter
    def position(self, position):
        """ Actual position of the viewport """

        self._requested_position = position
        self.root._compute_viewport()


    def _compute_viewport(self):
        """ Compute actual viewport in absolute coordinates """


        # Root requests are always honored, modulo the aspect
        if self.parent is None:
            w,h = self._requested_size
            if self._aspect:
                h = w * self._aspect
                if h > self._requested_size[1]:
                    h = self._requested_size[1]
                    w = h/self._aspect
            x = (self._requested_size[0] - w)/2
            y = (self._requested_size[1] - h)/2
            self._position          = x,y
            self._size              = w,h
            self._viewport_position = x,y
            self._viewport_size     = w,h
            self._scissor_position  = x,y
            self._scissor_size      = w,h
            for child in self._children:
                child._compute_viewport()
            return

        # Children viewport request depends on parent viewport
        pvx, pvy = self.parent._viewport_position
        pvw, pvh = self.parent._viewport_size
        psx, psy = self.parent._scissor_position
        psw, psh = self.parent._scissor_size

        # Relative width (to actual parent viewport)
        # ------------------------------------------
        if self._requested_size[0] <= -1.0:
            vw = max(pvw + self._requested_size[0],0)
        elif self._requested_size[0] < 0.0:
            vw = max(pvw + self._requested_size[0]*pvw,0)
        elif self._requested_size[0] <= 1.0:
            vw = self._requested_size[0]*pvw
        # Absolute width
        else:
            vw = self._requested_size[0]
        vw = int(round(vw))

        # Enforce aspect first
        if self._aspect:
            vh = self._aspect*vw
            if vh > pvh and -1 < self._requested_size[0] <= 1:
                vh = pvh
                vw = vh/self._aspect



        # Relative height (to actual parent viewport)
        # -------------------------------------------
        else:
            if self._requested_size[1] <= -1.0:
                vh = max(pvh + self._requested_size[1],0)
            elif self._requested_size[1] < 0.0:
                vh = max(pvh + self._requested_size[1]*pvh,0)
            elif self._requested_size[1] <= 1.0:
                vh = self._requested_size[1]*pvh
            # Absolute height
            else:
                vh = self._requested_size[1]
        vh = int(round(vh))

        # X anchor
        # ---------------------------------------
        if self._anchor[0] <= -1.0:
            ax = vw + self._anchor[0]
        elif self._anchor[0] < 0.0:
            ax = vw + self._anchor[0]*vw
        elif self._anchor[0] < 1.0:
            ax = self._anchor[0]*vw
        else:
            ax = self._anchor[0]
        ax = int(round(ax))

        # X positioning
        # ---------------------------------------
        if self._requested_position[0] <= -1.0:
            vx = pvw + self._requested_position[0]
        elif -1.0 < self._requested_position[0] < 0.0:
            vx = pvw + self._requested_position[0]*pvw
        elif 0.0 <= self._requested_position[0] < 1.0:
            vx = self._requested_position[0]*pvw
        else:
            vx = self._requested_position[0]
        vx = int(round(vx)) + pvx - ax

        # Y anchor
        # ---------------------------------------
        if self._anchor[1] <= -1.0:
            ay = vh + self._anchor[1]
        elif -1.0 < self._anchor[1] < 0.0:
            ay = vh + self._anchor[1]*vh
        elif 0.0 <= self._anchor[1] < 1.0:
            ay = self._anchor[1]*vh
        else:
            ay = self._anchor[1]
        ay = int(round(ay))

        # Y positioning
        # ---------------------------------------
        if self._requested_position[1] <= -1.0:
            vy = pvh + self._requested_position[1] #- vh
        elif -1.0 < self._requested_position[1] < 0.0:
            vy = pvh + self._requested_position[1]*pvh

        elif 0.0 <= self._requested_position[1] < 1.0:
            vy = self._requested_position[1]*pvh
        else:
            vy = self._requested_position[1]
        vy = int(round(vy)) + pvy - ay


        # Compute scissor size & position
        sx = max(pvx,vx)
        sy = max(pvy,vy)
        sw = max(min(psw-(sx-pvx)-1,vw), 0)
        sh = max(min(psh-(sy-pvy)-1,vh), 0)

        # Update internal information
        self._viewport_size     = vw, vh
        self._viewport_position = vx, vy
        self._scissor_size      = sw, sh
        self._scissor_position  = sx, sy

        # Update children
        for child in self._children:
            child._compute_viewport()


    def __contains__(self, (x,y)):
        # WARN: mouse pointer is usually upside down
        y = self.root.size[1] - y
        return ( x >= self._viewport_position[0] and
                 x < self._viewport_position[0] + self._viewport_size[0] and
                 y >= self._viewport_position[1] and
                 y < self._viewport_position[1] + self._viewport_size[1])

    # def lock(self):
    #     vx, vy = self._viewport_position
    #     vw, vh = self._viewport_size
    #     sx, sy = self._scissor_position
    #     sw, sh = self._scissor_size
    #     gl.glPushAttrib( gl.GL_VIEWPORT_BIT | gl.GL_SCISSOR_BIT )
    #     gl.glViewport( vx, vy, vw, vh )
    #     gl.glEnable( gl.GL_SCISSOR_TEST )
    #     gl.glScissor( sx, sy, sw+1, sh+1 )

    # def unlock(self):
    #     gl.glPopAttrib( )


    def on_resize(self, width, height):
        if self.parent == None:
            self._requested_size = width, height

        self._compute_viewport()

        if (self._transform._programs):
            self._transform["iResolution"] = width, height
            self._transform["viewport"] = self.viewport
        if (self._clipping._programs):
            self._clipping["iResolution"] = width, height
            self._clipping["viewport"] = self.viewport

        for child in self._children:
            child.dispatch_event("on_resize", width, height)


    def on_key_press(self, key, modifiers):
        """" Default key handler that close window on escape """
        pass

        # if key == window.key.ESCAPE:
        #     self.close()
        #     return True

    def on_mouse_press(self, x, y, button):
        if self.parent == None:
            self._active_viewports = []
        for child in self._children:
            if (x,y) in child:
                self.root._active_viewports.append(child)
                child.dispatch_event("on_mouse_press", x, y, button)


    def on_mouse_release(self, x, y, button):
        if self.parent == None:
            for child in self._active_viewports:
                child.dispatch_event("on_mouse_release", x, y, button)


    def on_mouse_drag(self, x, y, dx, dy, button):
        if self.parent == None:
            if self.root._active_viewports:
                child = self.root._active_viewports[-1]
                child.dispatch_event("on_mouse_drag", x, y, dx, dy, button)


    def on_mouse_scroll(self, x, y, dx, dy):
        if self.parent == None:
            if self.root._active_viewports:
                child = self.root._active_viewports[-1]
                child.dispatch_event("on_mouse_scroll", x, y, dx, dy)


    def on_mouse_motion(self, x, y, dx, dy):
        for child in self._children:
            if (x,y) in child:
                if not child._active:
                    child.dispatch_event("on_enter")
                self.active = False
                child._active = True
                child.dispatch_event("on_mouse_motion", x, y, dx, dy)
            else:
                if child._active:
                    child.dispatch_event("on_leave")
                child.active = False
                if (x,y) in self:
                    self._active = True


    def __replines__(self):
        """ ASCII display of trees by Andrew Cooke """
        yield "%s (%dx%d%+d%+d)" % (self.name,
                                    self.size[0], self.size[1],
                                    self.position[0], self.position[1])
        last = self._children[-1] if self._children else None
        for child in self._children:
            prefix = '└── ' if child is last else '├── '
            for line in child.__replines__():
                yield prefix + line
                prefix = '    ' if child is last else '│   '

    def __str__(self):
        return '\n'.join(self.__replines__()) + '\n'


# Viewport events
Viewport.register_event_type('on_enter')
Viewport.register_event_type('on_leave')
Viewport.register_event_type('on_resize')
Viewport.register_event_type('on_mouse_motion')
Viewport.register_event_type('on_mouse_drag')
Viewport.register_event_type('on_mouse_press')
Viewport.register_event_type('on_mouse_release')
Viewport.register_event_type('on_mouse_scroll')
Viewport.register_event_type('on_character')
Viewport.register_event_type('on_key_press')
Viewport.register_event_type('on_key_release')

# Viewport.register_event_type('on_draw')

# Window events
#Viewport.register_event_type('on_init')
#Viewport.register_event_type('on_show')
#Viewport.register_event_type('on_hide')
#Viewport.register_event_type('on_close')
#Viewport.register_event_type('on_idle')
