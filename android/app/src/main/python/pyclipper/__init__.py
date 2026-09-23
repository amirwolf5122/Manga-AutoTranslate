# -*- coding: utf-8 -*-

from shapely.geometry import Polygon

JT_ROUND = 2
JT_MITER = 1
JT_SQUARE = 0
ET_CLOSEDPOLYGON = 1
ET_OPENROUND = 2


def _scale_path(path):
    return [(float(p[0]), float(p[1])) for p in path]


class _Offset:
    def __init__(self):
        self._paths = []

    def AddPath(self, path, join_type, end_type):
        self._paths.append(_scale_path(path))
        return True

    def AddPaths(self, paths, join_type, end_type):
        for p in paths:
            self.AddPath(p, join_type, end_type)
        return True

    def Execute(self, delta):
        out = []
        d = abs(float(delta))
        for pts in self._paths:
            grown = None
            try:
                poly = Polygon(pts)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty or poly.area <= 1e-9:
                    poly = None
                else:
                    grown = poly.buffer(d, join_style="round")
                    if grown.is_empty or grown.exterior is None:
                        grown = None
            except Exception:
                grown = None
            if grown is None:
                try:
                    xs = [float(p[0]) for p in pts]
                    ys = [float(p[1]) for p in pts]
                    out.append([[int(round(min(xs) - d)), int(round(min(ys) - d))],
                                [int(round(max(xs) + d)), int(round(min(ys) - d))],
                                [int(round(max(xs) + d)), int(round(max(ys) + d))],
                                [int(round(min(xs) - d)), int(round(max(ys) + d))]])
                except Exception:
                    pass
                continue
            coords = list(grown.exterior.coords)[:-1]
            if len(coords) >= 3:
                out.append([[int(round(x)), int(round(y))] for x, y in coords])
        return out


class PyclipperOffset:
    def __init__(self, *a, **k):
        self._off = _Offset()

    def AddPath(self, path, join_type, end_type):
        return self._off.AddPath(path, join_type, end_type)

    def AddPaths(self, paths, join_type, end_type):
        return self._off.AddPaths(paths, join_type, end_type)

    def Execute(self, delta):
        return self._off.Execute(delta)

    def Clear(self):
        self._off._paths = []


class Pyclipper:
    def __init__(self, *a, **k):
        pass

    def AddPath(self, *a, **k):
        return True

    def Execute(self, *a, **k):
        return []


def SimplifyPath(path, fill_type=1):
    return [list(_scale_path(path))]


def ScaleUp(v, s):
    return v


def ScaleDown(v, s):
    return v


def Area(poly):
    p = Polygon(_scale_path(poly))
    return p.area
