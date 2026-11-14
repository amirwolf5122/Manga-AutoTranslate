# -*- coding: utf-8 -*-

import numpy as np

__version__ = "1.31.0-android-shim-v4"


def preload_dlls(*a, **k):
    pass

try:
    from java import jclass, jarray
    try:
        from java import (jfloat as _JF, jdouble as _JD, jlong as _JL,
                          jint as _JI, jbyte as _JB)
    except Exception:
        _JF = _JD = _JL = _JI = _JB = None
    _FloatBuffer = jclass("java.nio.FloatBuffer")
    _LongBuffer = jclass("java.nio.LongBuffer")
    _IntBuffer = jclass("java.nio.IntBuffer")
    _ByteBuffer = jclass("java.nio.ByteBuffer")
    _DoubleBuffer = jclass("java.nio.DoubleBuffer")
    _HashMap = jclass("java.util.HashMap")
    _OrtEnvironment = jclass("ai.onnxruntime.OrtEnvironment")
    _OrtSession_cls = jclass("ai.onnxruntime.OrtSession$SessionOptions")
    _OnnxTensor = jclass("ai.onnxruntime.OnnxTensor")
    _ENV = _OrtEnvironment.getEnvironment()
    _OK = True
    _IMPORT_ERR = None
except Exception as _e:
    _OK = False
    _IMPORT_ERR = _e


_JCODE_TYPE = {"f": ("JF", "float"), "d": ("JD", "double"),
               "j": ("JL", "long"), "i": ("JI", "int"), "b": ("JB", "byte")}
_JSTRAT = {"n": 0}


def _prim_cls(name):
    box = {"float": "Float", "double": "Double", "long": "Long",
           "int": "Integer", "byte": "Byte"}[name]
    return jclass("java.lang." + box).TYPE


def _jarr_fill(seq, code):
    seq = list(seq)
    s = _JSTRAT["n"]
    if s == 0 or s == 1:
        try:
            tname, prim = _JCODE_TYPE[code]
            jt = {"JF": _JF, "JD": _JD, "JL": _JL, "JI": _JI,
                  "JB": _JB}.get(tname)
            if jt is None:
                jt = _prim_cls(prim)
            arr = jarray(jt)(seq)
            _JSTRAT["n"] = 1
            return arr
        except Exception:
            if s == 1:
                raise
            _JSTRAT["n"] = 2
    if s == 0 or s == 2:
        try:
            arr = jarray.zeros(len(seq), code)
            for i, v in enumerate(seq):
                arr[i] = v
            _JSTRAT["n"] = 2
            return arr
        except Exception:
            if s == 2:
                raise
            _JSTRAT["n"] = 3
    prim = _JCODE_TYPE[code][1]
    _Arr = jclass("java.lang.reflect.Array")
    arr = _Arr.newInstance(_prim_cls(prim), len(seq))
    for i, v in enumerate(seq):
        arr[i] = v
    return arr


class ExecutionMode:

    ORT_SEQUENTIAL = 0
    ORT_PARALLEL = 1


class GraphOptimizationLevel:

    ORT_DISABLE_ALL = 0
    ORT_ENABLE_BASIC = 1
    ORT_ENABLE_EXTENDED = 2
    ORT_ENABLE_ALL = 99


_OPTLEVEL_NAMES = {
    0: "ORT_DISABLE_ALL", 1: "ORT_ENABLE_BASIC",
    2: "ORT_ENABLE_EXTENDED", 99: "ORT_ENABLE_ALL",
}


class SessionOptions:

    def __init__(self):
        self.intra_op_num_threads = 3
        self.inter_op_num_threads = 1
        self.optimized_model_filepath = ""
        self.graph_optimization_level = GraphOptimizationLevel.ORT_ENABLE_ALL
        self._eps = []
        self._cfg = {}

    def append_execution_provider(self, name, opts=None):
        try:
            self._eps.append((str(name), dict(opts or {})))
        except Exception:
            self._eps.append((str(name), {}))

    def __setattr__(self, k, v):
        self.__dict__[k] = v

    def add_session_config_entry(self, k, v=None):
        try:
            self._cfg[str(k)] = str(v)
        except Exception:
            pass


def get_available_providers():
    return ["CPUExecutionProvider", "XnnpackExecutionProvider",
            "NnapiExecutionProvider"]


def get_device():
    return "CPU"


def _jmap_to_dict(m):
    out = {}
    try:
        it = m.entrySet().iterator()
        while it.hasNext():
            e = it.next()
            out[str(e.getKey())] = str(e.getValue())
        if out:
            return out
    except Exception:
        pass
    try:
        arr = m.entrySet().toArray()
        for e in list(arr):
            out[str(e.getKey())] = str(e.getValue())
    except Exception:
        pass
    return out


def _jset_to_list(js):
    out = []
    try:
        it = js.iterator()
        while it.hasNext():
            out.append(str(it.next()))
    except Exception:
        try:
            out = [str(x) for x in js.toArray()]
        except Exception:
            pass
    return out


class NodeArg:
    def __init__(self, name, shape=None, dtype="tensor(float)"):
        self.name = name
        self.shape = list(shape) if shape else []
        self.type = dtype

    def __repr__(self):
        return "NodeArg(%r, %r, %r)" % (self.name, self.shape, self.type)


def _buf_of(ja, code):
    if code == "f":
        return _FloatBuffer.wrap(ja)
    if code == "j":
        return _LongBuffer.wrap(ja)
    if code == "i":
        return _IntBuffer.wrap(ja)
    if code == "d":
        return _DoubleBuffer.wrap(ja)
    return _ByteBuffer.wrap(ja)


def _tensor_create(x):

    if not isinstance(x, np.ndarray):
        x = np.asarray(x)
    if x.dtype == np.float64:
        x = x.astype(np.float32)
    if x.dtype in (np.int16, np.uint16, np.uint32, np.uint64, np.bool_):
        x = x.astype(np.int64) if x.dtype == np.bool_ else x.astype(np.float32)
    x = np.ascontiguousarray(x)
    shape = _jarr_fill([int(v) for v in x.shape], "j")
    if x.dtype == np.float32:
        try:
            ja = jarray(_JF)(x.reshape(-1))
            return _OnnxTensor.createTensor(_ENV, _buf_of(ja, "f"), shape)
        except Exception:
            pass
    elif x.dtype in (np.uint8, np.int8):
        try:
            ja = jarray(_JB)(x.reshape(-1))
            return _OnnxTensor.createTensor(_ENV, _buf_of(ja, "b"), shape)
        except Exception:
            pass
    elif x.dtype == np.int64:
        try:
            ja = jarray(_JL)(x.reshape(-1))
            return _OnnxTensor.createTensor(_ENV, _buf_of(ja, "j"), shape)
        except Exception:
            pass
    elif x.dtype == np.int32:
        try:
            ja = jarray(_JI)(x.reshape(-1))
            return _OnnxTensor.createTensor(_ENV, _buf_of(ja, "i"), shape)
        except Exception:
            pass
    flat = x.ravel()
    if x.dtype == np.float32:
        code = "f"
    elif x.dtype == np.int64:
        code = "j"
    elif x.dtype == np.int32:
        code = "i"
    elif x.dtype in (np.uint8, np.int8):
        code = "b"
    else:
        flat = flat.astype(np.float32)
        code = "f"
    ja = _jarr_fill(flat.tolist(), code)
    return _OnnxTensor.createTensor(_ENV, _buf_of(ja, code), shape)


def _to_numpy(value):
    def conv(v):
        try:
            it = iter(v)
        except TypeError:
            return v
        return [conv(x) for x in it]
    arr = np.asarray(conv(value))
    if arr.dtype == np.float64:
        arr = arr.astype(np.float32)
    return arr


def _tensor_out_to_numpy(t):
    try:
        shape = []
        try:
            shape = [int(v) for v in list(t.getInfo().getShape())]
        except Exception:
            return None
        fb = t.getFloatBuffer()
        mv = memoryview(fb)
        arr = np.frombuffer(mv, dtype=np.float32)
        n = 1
        for d in shape:
            n *= int(d)
        if arr.size != n:
            return None
        return arr.reshape(shape).copy()
    except Exception:
        return None


def _result_value(result, name):
    try:
        it = result.iterator()
        while it.hasNext():
            e = it.next()
            if str(e.getKey()) == str(name):
                return e.getValue()
    except Exception:
        pass
    try:
        t = result.get(name)
    except Exception:
        t = None
    if t is None:
        return None
    try:
        if hasattr(t, "isPresent"):
            return t.get() if t.isPresent() else None
    except Exception:
        pass
    return t


class _ModelMeta:
    def __init__(self, sess=None):
        self.producer_name = ""
        self.graph_name = ""
        self.description = ""
        self.custom_metadata_map = {}
        if sess is None:
            return
        md = None
        try:
            md = sess.getMetadata()
        except Exception:
            md = None
        if md is None:
            return

        cm = None
        try:
            cm = md.getCustomMetadata()
        except Exception:
            cm = None
        if cm is None:
            try:
                cm = md.customMetadata
            except Exception:
                cm = None
        if cm is not None:
            self.custom_metadata_map = _jmap_to_dict(cm)
        try:
            self.producer_name = str(md.getProducerName() or "")
        except Exception:
            pass
        try:
            self.graph_name = str(md.getGraphName() or "")
        except Exception:
            pass
        try:
            self.description = str(md.getDescription() or "")
        except Exception:
            pass


_JTYPE2ORT = {
    "FLOAT": "tensor(float)", "DOUBLE": "tensor(double)",
    "INT8": "tensor(int8)", "INT16": "tensor(int16)",
    "INT32": "tensor(int32)", "INT64": "tensor(int64)",
    "UINT8": "tensor(uint8)", "BOOL": "tensor(bool)",
    "STRING": "tensor(string)", "BFLOAT16": "tensor(bfloat16)",
}


def _node_info(info):
    shape, dtype = [], "tensor(float)"
    js = None
    try:
        js = info.getShape()
    except Exception:
        pass
    if js is None:
        try:
            js = info.getInfo().getShape()
        except Exception:
            pass
    try:
        shape = [int(s) if s is not None else -1 for s in list(js)]
    except Exception:
        pass
    try:
        dtype = _JTYPE2ORT.get(str(info.getInfo().getType()), "tensor(float)")
    except Exception:
        pass
    return shape, dtype


def _apply_java_eps(jopt, sess_options):
    try:
        eps = list(getattr(sess_options, "_eps", []) or [])
    except Exception:
        eps = []
    used = []
    for name, popts in eps:
        try:
            if name == "XnnpackExecutionProvider":
                mp = _HashMap()
                try:
                    for k, v in dict(popts or {}).items():
                        mp.put(str(k), str(v))
                except Exception:
                    pass
                jopt.addXnnpack(mp)
                used.append(name)
            elif name == "NnapiExecutionProvider":
                try:
                    jopt.addNnapi()
                except Exception:
                    try:
                        _HS = jclass("java.util.HashSet")
                        jopt.addNnapi(_HS())
                    except Exception:
                        continue
                used.append(name)
            elif name == "WebGpuExecutionProvider":
                if not hasattr(jopt, "addWebGPU"):
                    continue
                try:
                    jopt.addWebGPU()
                    used.append(name)
                except Exception:
                    continue
        except Exception:
            continue
    return used


def _build_java_session_options(sess_options):
    if sess_options is None:
        return None
    jopt = None
    try:
        jopt = _OrtSession_cls()
    except Exception:
        return None
    try:
        thr = int(getattr(sess_options, "intra_op_num_threads", 0) or 0)
        if thr > 0:
            jopt.setIntraOpNumThreads(thr)
    except Exception:
        pass
    try:
        inter = int(getattr(sess_options, "inter_op_num_threads", 1) or 1)
        jopt.setInterOpNumThreads(max(1, inter))
    except Exception:
        pass
    try:
        lv = getattr(sess_options, "graph_optimization_level", None)
        name = None
        if lv is not None:
            name = getattr(lv, "name", None)
            if name is None:
                try:
                    name = _OPTLEVEL_NAMES.get(int(lv))
                except Exception:
                    name = None
        if name:
            _Ol = jclass(
                "ai.onnxruntime.OrtSession$SessionOptions$OptLevel")
            jopt.setOptimizationLevel(getattr(_Ol, name))
    except Exception:
        pass
    try:
        em = getattr(sess_options, "execution_mode", None)
        if em is not None:
            _Em = jclass(
                "ai.onnxruntime.OrtSession$SessionOptions$ExecutionMode")
            ename = getattr(em, "name", None) or (
                "ORT_SEQUENTIAL" if int(em) == 0 else "ORT_PARALLEL")
            jopt.setExecutionMode(getattr(_Em, ename))
    except Exception:
        pass
    try:
        jopt.setCPUArenaAllocator(bool(
            getattr(sess_options, "enable_cpu_mem_arena", True)))
    except Exception:
        pass
    try:
        jopt.setMemoryPatternOptimization(bool(
            getattr(sess_options, "enable_mem_pattern", True)))
    except Exception:
        pass
    try:
        p = str(getattr(sess_options, "optimized_model_filepath", "") or "")
        if p:
            jopt.setOptimizedModelFilePath(p)
    except Exception:
        pass
    try:
        _apply_java_eps(jopt, sess_options)
    except Exception:
        pass
    try:
        _cfg = dict(getattr(sess_options, "_cfg", {}) or {})
        for _ck in _cfg:
            try:
                jopt.addSessionConfigEntry(str(_ck), str(_cfg[_ck]))
            except Exception:
                pass
    except Exception:
        pass
    return jopt


class InferenceSession:
    def __init__(self, path_or_bytes, sess_options=None, providers=None, **kw):
        if not _OK:
            raise ImportError("شیم ORT اندروید لود نشد: %s" % (_IMPORT_ERR,))
        try:
            if providers:
                for _p in providers:
                    _pn = str(_p)
                    if _pn != "CPUExecutionProvider" and not any(
                            e[0] == _pn for e in getattr(sess_options, "_eps", [])):
                        sess_options.append_execution_provider(_pn)
        except Exception:
            pass
        jopt = _build_java_session_options(sess_options)
        if isinstance(path_or_bytes, (bytes, bytearray)):
            import os
            import tempfile
            fd, tmp = tempfile.mkstemp(suffix=".onnx")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(path_or_bytes)
                if jopt is not None:
                    self._sess = _ENV.createSession(tmp, jopt)
                else:
                    self._sess = _ENV.createSession(tmp)
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        else:
            if jopt is not None:
                self._sess = _ENV.createSession(str(path_or_bytes), jopt)
            else:
                self._sess = _ENV.createSession(str(path_or_bytes))
        self._in_names = _jset_to_list(self._sess.getInputNames())
        self._out_names = _jset_to_list(self._sess.getOutputNames())
        try:
            self._prov = ["CPUExecutionProvider"] + [
                e[0] for e in list(getattr(sess_options, "_eps", []) or [])]
        except Exception:
            self._prov = ["CPUExecutionProvider"]

    def get_inputs(self):
        infos = None
        try:
            infos = self._sess.getInputInfo()
        except Exception:
            pass
        out = []
        for name in self._in_names:
            shape, dtype = [], "tensor(float)"
            if infos is not None:
                try:
                    info = infos.get(name)
                except Exception:
                    info = None
                if info is not None:
                    shape, dtype = _node_info(info)
            out.append(NodeArg(name, shape, dtype))
        return out

    def get_outputs(self):
        infos = None
        try:
            infos = self._sess.getOutputInfo()
        except Exception:
            pass
        out = []
        for name in self._out_names:
            shape, dtype = [], "tensor(float)"
            if infos is not None:
                try:
                    info = infos.get(name)
                except Exception:
                    info = None
                if info is not None:
                    shape, dtype = _node_info(info)
            out.append(NodeArg(name, shape, dtype))
        return out

    def get_modelmeta(self):
        return _ModelMeta(self._sess)

    def get_providers(self):
        try:
            return list(self._prov)
        except Exception:
            return ["CPUExecutionProvider"]

    def get_provider_options(self):
        try:
            return {p: {} for p in self._prov}
        except Exception:
            return {"CPUExecutionProvider": {}}

    def run(self, output_names, input_feed, run_options=None, **kw):
        feed = _HashMap()
        for name, x in input_feed.items():
            feed.put(str(name), _tensor_create(x))
        result = self._sess.run(feed)
        names = [str(n) for n in output_names] if output_names else self._out_names
        outs = []
        for name in names:
            t = _result_value(result, name)
            if t is None:
                outs.append(None)
                continue
            try:
                fast = _tensor_out_to_numpy(t)
                if fast is not None:
                    outs.append(fast)
                else:
                    outs.append(_to_numpy(t.getValue()))
            finally:
                try:
                    t.close()
                except Exception:
                    pass
        return outs
