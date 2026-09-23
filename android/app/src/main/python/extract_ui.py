# -*- coding: utf-8 -*-

import ast
import copy
import json
import re

_GR_NAMES = ("gr", "_gr")
_WIDGETS = {
    "Dropdown": "select",
    "Radio": "radio",
    "Checkbox": "bool",
    "Textbox": "text",
    "Slider": "slider",
    "File": "file",
    "Number": "number",
}
_HTML = "HTML"
_ACC = "Accordion"

_UNKNOWN = object()


class _Env:


    def __init__(self, tree):
        self.scopes = [{}]
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                v = _eval(node.value, self)
                if v is not _UNKNOWN:
                    self.scopes[0][node.targets[0].id] = v

    def push(self, binding):
        self.scopes.append(dict(binding))

    def pop(self):
        self.scopes.pop()

    def get(self, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return _UNKNOWN


def _eval(node, env):
    if node is None:
        return _UNKNOWN
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.JoinedStr):
        parts = []
        for x in node.values:
            v = _eval(x, env)
            if v is _UNKNOWN:
                return _UNKNOWN
            parts.append(str(v))
        return "".join(parts)
    if isinstance(node, ast.FormattedValue):
        return _eval(node.value, env)
    if isinstance(node, ast.Tuple) or isinstance(node, ast.List):
        vals = [_eval(e, env) for e in node.elts]
        if any(v is _UNKNOWN for v in vals):
            return _UNKNOWN
        return tuple(vals) if isinstance(node, ast.Tuple) else list(vals)
    if isinstance(node, ast.Dict):
        keys = [_eval(k, env) for k in node.keys]
        vals = [_eval(v, env) for v in node.values]
        if any(v is _UNKNOWN or k is _UNKNOWN for k, v in zip(keys, vals)):
            return _UNKNOWN
        return dict(zip(keys, vals))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand, env)
        if v is _UNKNOWN or not isinstance(v, (int, float)):
            return _UNKNOWN
        return -v if isinstance(node.op, ast.USub) else +v
    if isinstance(node, ast.BinOp):
        a, b = _eval(node.left, env), _eval(node.right, env)
        if a is _UNKNOWN or b is _UNKNOWN:
            return _UNKNOWN
        op = type(node.op)
        try:
            if op is ast.Add:
                return a + b
            if op is ast.Sub:
                return a - b
            if op is ast.Mult:
                return a * b
            if op is ast.FloorDiv:
                return a // b
            if op is ast.Mod:
                return a % b
        except Exception:
            return _UNKNOWN
        return _UNKNOWN
    if isinstance(node, ast.Compare):
        a, b = _eval(node.left, env), _eval(node.comparators[0], env)
        if a is _UNKNOWN or b is _UNKNOWN:
            return _UNKNOWN
        if isinstance(node.ops[0], ast.Eq):
            return a == b
        if isinstance(node.ops[0], ast.NotEq):
            return a != b
        return _UNKNOWN
    if isinstance(node, ast.BoolOp):
        return _UNKNOWN
    if isinstance(node, ast.IfExp):
        c = _eval(node.test, env)
        if c is _UNKNOWN:
            body, orelse = _eval(node.body, env), _eval(node.orelse, env)
            return body if (body is not _UNKNOWN and body == orelse) else _UNKNOWN
        return _eval(node.body if c else node.orelse, env)
    if isinstance(node, ast.Subscript):
        base = _eval(node.value, env)
        if base is _UNKNOWN:
            return _UNKNOWN
        sl = node.slice
        if isinstance(sl, ast.Slice):
            lo = _eval(sl.lower, env)
            hi = _eval(sl.upper, env)
            st = _eval(sl.step, env)
            try:
                return base[(slice(lo if lo is not _UNKNOWN else None,
                                   hi if hi is not _UNKNOWN else None,
                                   st if st is not _UNKNOWN else None))]
            except Exception:
                return _UNKNOWN
        idx = _eval(sl, env)
        if idx is _UNKNOWN:
            return _UNKNOWN
        try:
            return base[int(idx)]
        except Exception:
            return _UNKNOWN
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name) and f.id in ("len", "list", "str", "int",
                                                "float", "bool", "tuple"):
            args = [_eval(a, env) for a in node.args]
            if any(a is _UNKNOWN for a in args):
                return _UNKNOWN
            try:
                return {"len": len, "list": list, "str": str, "int": int,
                        "float": float, "bool": bool, "tuple": tuple}[f.id](*args)
            except Exception:
                return _UNKNOWN
        if (isinstance(f, ast.Attribute) and f.attr == "get"
                and not node.keywords):
            recv = _eval(f.value, env)
            if isinstance(recv, dict):
                keys = [_eval(a, env) for a in node.args]
                if keys and keys[0] is not _UNKNOWN:
                    try:
                        return recv.get(keys[0],
                                        keys[1] if len(keys) > 1 else None)
                    except Exception:
                        return _UNKNOWN
        return _UNKNOWN
    if isinstance(node, ast.Starred):
        return _UNKNOWN
    return _UNKNOWN


def _eval_iterable(expr, env):
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) \
            and expr.func.id == "enumerate" and expr.args:
        inner = _eval_iterable(expr.args[0], env)
        if inner is None:
            return None
        return list(enumerate(inner))
    v = _eval(expr, env)
    if v is _UNKNOWN or not isinstance(v, (list, tuple)):
        return None
    return list(v)


def _iter_values(node, env):
    if not isinstance(node, ast.For):
        return None
    return _eval_iterable(node.iter, env)


def _bind(target, value):
    binding = {}
    if isinstance(target, ast.Name):
        binding[target.id] = value
        return binding
    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (list, tuple)) \
            and len(target.elts) == len(value):
        for t, v in zip(target.elts, value):
            b = _bind(t, v)
            if b is None:
                return None
            binding.update(b)
        return binding
    return None


class _Snap:

    def __init__(self, scopes):
        self.scopes = scopes

    def get(self, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return _UNKNOWN


def _lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def _str_of(node, env=None):
    if node is None:
        return None
    if env is not None and isinstance(node, (ast.JoinedStr, ast.FormattedValue)):
        if isinstance(node, ast.FormattedValue):
            v = _eval(node.value, env)
            return v if isinstance(v, str) and v.strip() else None
        parts = []
        for x in node.values:
            v = _eval(x, env)
            if isinstance(v, str):
                parts.append(v)
            elif v is _UNKNOWN:
                continue
            elif v is not None:
                parts.append(str(v))
        s = "".join(parts)
        return s if s.strip() else None
    v = _lit(node)
    if isinstance(v, str):
        return v
    if isinstance(node, ast.JoinedStr):
        parts = []
        for x in node.values:
            if isinstance(x, ast.Constant) and x.value is not None:
                parts.append(str(x.value))
        s = "".join(parts)
        return s if s.strip() else None
    return None


def _choices(node):
    if node is None:
        return None
    try:
        vals = ast.literal_eval(node)
    except Exception:
        return None
    if not isinstance(vals, (list, tuple)):
        return None
    out = []
    for v in vals or []:
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            out.append([str(v[0]), str(v[1])])
        else:
            out.append([str(v), str(v)])
    return out


def _default(node):
    if node is None:
        return None, None
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name) and f.id in ("str", "int", "float", "bool") \
                and node.args:
            return _default(node.args[0])
        if (isinstance(f, ast.Attribute) and f.attr == "get"
                and isinstance(f.value, ast.Name) and f.value.id == "cfg"):
            key = _lit(node.args[0]) if node.args else None
            dflt = _lit(node.args[1]) if len(node.args) > 1 else None
            if dflt is None:
                for kw in node.keywords:
                    if kw.arg == "default":
                        dflt = _lit(kw.value)
            return {"cfg": key, "default": dflt}, key
        return None, None
    return _lit(node), None


def _assign_name(parent_stack):
    for p in reversed(parent_stack):
        if isinstance(p, ast.Assign) and p.targets:
            t = p.targets[0]
            if isinstance(t, ast.Name):
                return t.id
    return None


def _unwrap_safe(tree):

    class W(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            f = node.func
            if (isinstance(f, ast.Name) and f.id == "_safe" and node.args
                    and isinstance(node.args[0], ast.Attribute)
                    and getattr(node.args[0].value, "id", None) in ("gr", "_gr")):
                new = ast.Call(
                    func=node.args[0],
                    args=[copy.deepcopy(a) for a in node.args[1:]],
                    keywords=[ast.keyword(kw.arg, copy.deepcopy(kw.value))
                              for kw in node.keywords if kw.arg],
                )
                return ast.copy_location(new, node)
            return node

    return W().visit(tree)


def extract(path_or_source, is_source=False):
    src = path_or_source if is_source else open(path_or_source, encoding="utf-8").read()
    tree = ast.parse(src)
    _unwrap_safe(tree)

    env = _Env(tree)
    calls = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []
            self.tag = ""
            self.seq = 0

        def generic_visit(self, node):

            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                v = _eval(node.value, env)
                if v is not _UNKNOWN:
                    env.scopes[0][node.targets[0].id] = v
            if isinstance(node, ast.For):
                vals = _iter_values(node, env)
                if vals is not None:
                    for i, val in enumerate(vals):
                        binding = _bind(node.target, val)
                        if binding is None:
                            continue
                        env.push(binding)
                        old_tag = self.tag
                        str_b = [v for v in binding.values()
                                 if isinstance(v, str) and v.strip()]
                        self.tag = str_b[0] if str_b else str(i)
                        for stmt in node.body:
                            self.visit(stmt)
                        self.tag = old_tag
                        env.pop()
                    for stmt in node.orelse:
                        self.visit(stmt)
                    return
            self.stack.append(node)
            if isinstance(node, ast.Call):
                calls.append((self.seq, node, list(self.stack), self.tag,
                              _Snap([dict(s) for s in env.scopes])))
                self.seq += 1
            super().generic_visit(node)
            self.stack.pop()

    V().visit(tree)
    
    app_ver = "0"
    m = re.search(r'APP_VER\s*=\s*"([^"]+)"', src)
    if m:
        app_ver = m.group(1)

    items = []
    for _seq, node, stack, tag, env_snap in calls:
        f = node.func
        if not (isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Name)
                and f.value.id in _GR_NAMES):
            continue
        kind = f.attr
        kw = {k.arg: k.value for k in node.keywords if k.arg}

        if kind in _WIDGETS:
            fid = _lit(kw.get("elem_id")) or _assign_name(stack) or ("f%d" % node.lineno)
            if tag and not str(fid).endswith("_" + tag):
                fid = "%s_%s" % (fid, tag)
            label = _str_of(kw.get("label"), env_snap) or ""
            info = _str_of(kw.get("info"), env_snap) or ""
            value, cfg_key = _default(kw.get("value"))
            choices = _choices(kw.get("choices"))
            if choices is None and node.args:
                ch = _choices(node.args[0])
                if isinstance(ch, list) and ch:
                    choices = ch
                elif isinstance(node.args[0], ast.Name) and node.args[0].id == "PROVIDERS":
                    choices = None
                    fid = fid if fid != "" else "provider"
            field = {
                "id": fid,
                "type": _WIDGETS[kind],
                "label": label,
                "default": value,
            }
            if info:
                field["info"] = info
            if choices is not None:
                field["choices"] = choices
            if choices is None and kind == "Dropdown":
                field["choices_from"] = "PROVIDERS"
            if cfg_key:
                field["cfg"] = cfg_key
            if kind == "Textbox":
                t = _lit(kw.get("type"))
                if t == "password":
                    field["password"] = True
                ph = _str_of(kw.get("placeholder"), env_snap)
                if ph:
                    field["placeholder"] = ph
                ln = _lit(kw.get("lines"))
                if isinstance(ln, int) and ln > 1:
                    field["lines"] = ln
            if kind == "Slider":
                pos = [_lit(a) for a in node.args]
                field["min"] = pos[0] if pos else 0
                field["max"] = pos[1] if len(pos) > 1 else 100
                st = _lit(kw.get("step"))
                field["step"] = st or 1
            if kind == "File":
                ft = _lit(kw.get("file_types"))
                if ft:
                    field["accept"] = " ".join(ft)
            items.append(field)

        elif kind == _HTML:
            code = _lit(kw.get("value")) or (_lit(node.args[0]) if node.args else "") or ""
            if "steptitle" in str(code):
                txt = re.sub(r"<[^>]+>", " ", str(code))
                txt = re.sub(r"\s+", " ", txt).strip()
                if txt:
                    items.append({"type": "section", "title": txt})

        elif kind == _ACC:
            label = _str_of(kw.get("label"), env_snap) \
                or (_str_of(node.args[0], env_snap) if node.args else None)
            if label:
                items.append({"type": "accordion", "title": str(label)})

    _HIDDEN = {"manga_sid", "manga_sid_holder", "sid_holder", "manga_reader_url",
               "sid_box", "session_id"}
    sections = []
    cur = {"title": "تنظیمات", "fields": []}
    seen_ids = {}

    def _close():
        nonlocal cur
        if cur["fields"]:
            sections.append(cur)
        cur = {"title": "", "fields": []}

    for it in items:
        if it["type"] == "section":
            _close()
            cur["title"] = it["title"]
        elif it["type"] == "accordion":
            _close()
            cur["title"] = it["title"]
        else:
            if it.get("id") in _HIDDEN:
                continue
            if not (it.get("label") or it.get("info") or it.get("placeholder")):
                continue
            fid = it.get("id")
            if fid:
                n = seen_ids.get(fid, 0)
                seen_ids[fid] = n + 1
                if n:
                    it["id"] = "%s_%d" % (fid, n + 1)
            cur["fields"].append(it)
    _close()

    sections = [s for s in sections if s["fields"]]
    for i, s in enumerate(sections):
        if not s["title"]:
            s["title"] = "تنظیمات" if i == 0 else "بخش %d" % (i + 1)

    return {"app_name": "مانگا مترجم", "app_ver": app_ver, "sections": sections}


if __name__ == "__main__":
    import sys
    mf = extract(sys.argv[1] if len(sys.argv) > 1 else "manga_app.py")
    print(json.dumps(mf, ensure_ascii=False, indent=1))
