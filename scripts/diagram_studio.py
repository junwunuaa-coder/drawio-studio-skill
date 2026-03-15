#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

PAGE_PRESETS: dict[str, tuple[int, int]] = {
    "letter": (850, 1100),
    "a4": (827, 1169),
    "a3": (1169, 1654),
    "16:9": (1280, 720),
    "4:3": (1024, 768),
    "square": (800, 800),
    "custom": (850, 1100),
}

SHAPE_STYLES: dict[str, str] = {
    "rectangle": "rounded=0;whiteSpace=wrap;html=1;",
    "rounded": "rounded=1;whiteSpace=wrap;html=1;",
    "ellipse": "ellipse;whiteSpace=wrap;html=1;",
    "diamond": "rhombus;whiteSpace=wrap;html=1;",
    "triangle": "triangle;whiteSpace=wrap;html=1;",
    "hexagon": "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;",
    "cylinder": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;",
    "cloud": "shape=cloud;whiteSpace=wrap;html=1;",
    "parallelogram": "shape=parallelogram;whiteSpace=wrap;html=1;",
    "process": "shape=process;whiteSpace=wrap;html=1;backgroundOutline=1;",
    "document": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;",
    "callout": "shape=callout;whiteSpace=wrap;html=1;",
    "note": "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;",
    "actor": "shape=mxgraph.basic.person;whiteSpace=wrap;html=1;",
    "text": "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];",
}

EDGE_STYLES: dict[str, str] = {
    "straight": "edgeStyle=none;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
    "orthogonal": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
    "curved": "edgeStyle=orthogonalEdgeStyle;curved=1;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;",
    "entity-relation": "edgeStyle=entityRelationEdgeStyle;html=1;",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def find_drawio_bin() -> str | None:
    env = os.environ.get("DRAWIO_STUDIO_DRAWIO_BIN")
    if env and Path(env).exists():
        return env
    for n in ["draw.io", "drawio", "diagrams.net"]:
        p = shutil.which(n)
        if p:
            return p
    return None


@dataclass
class SessionStore:
    root: Path
    session_id: str

    @property
    def session_dir(self) -> Path:
        return self.root / self.session_id

    @property
    def meta_path(self) -> Path:
        return self.session_dir / "metadata.json"

    def load(self) -> dict[str, Any]:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        if not self.meta_path.exists():
            meta = {
                "session_id": self.session_id,
                "project_path": None,
                "history": [],
                "index": -1,
                "updated_at": now_iso(),
            }
            self.save(meta)
            return meta
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def save(self, meta: dict[str, Any]) -> None:
        meta["updated_at"] = now_iso()
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_project(self, path: Path, root: ET.Element) -> dict[str, Any]:
        meta = self.load()
        meta["project_path"] = str(path)
        meta["history"] = []
        meta["index"] = -1
        self.save(meta)
        return self.record_snapshot(root)

    def record_snapshot(self, root: ET.Element) -> dict[str, Any]:
        meta = self.load()
        # truncate redo branch
        idx = int(meta.get("index", -1))
        history: list[str] = list(meta.get("history", []))
        if idx < len(history) - 1:
            for stale in history[idx + 1 :]:
                sp = self.session_dir / stale
                if sp.exists():
                    sp.unlink()
            history = history[: idx + 1]

        fname = f"snap_{len(history):04d}.drawio"
        spath = self.session_dir / fname
        spath.write_bytes(xml_bytes(root))
        history.append(fname)
        meta["history"] = history
        meta["index"] = len(history) - 1
        self.save(meta)
        return meta

    def _load_snapshot(self, meta: dict[str, Any], idx: int) -> ET.Element:
        history: list[str] = list(meta.get("history", []))
        snap = self.session_dir / history[idx]
        return ET.fromstring(snap.read_bytes())

    def undo(self) -> tuple[dict[str, Any], ET.Element] | None:
        meta = self.load()
        idx = int(meta.get("index", -1))
        if idx <= 0:
            return None
        idx -= 1
        meta["index"] = idx
        self.save(meta)
        return meta, self._load_snapshot(meta, idx)

    def redo(self) -> tuple[dict[str, Any], ET.Element] | None:
        meta = self.load()
        idx = int(meta.get("index", -1))
        history: list[str] = list(meta.get("history", []))
        if idx >= len(history) - 1:
            return None
        idx += 1
        meta["index"] = idx
        self.save(meta)
        return meta, self._load_snapshot(meta, idx)


class DiagramProject:
    def __init__(self, root: ET.Element, path: Path | None = None):
        self.root = root
        self.path = path

    @staticmethod
    def _base_mxgraph(width: int, height: int) -> ET.Element:
        mx = ET.Element(
            "mxGraphModel",
            {
                "dx": "1200",
                "dy": "800",
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": str(width),
                "pageHeight": str(height),
                "math": "0",
                "shadow": "0",
            },
        )
        r = ET.SubElement(mx, "root")
        ET.SubElement(r, "mxCell", {"id": "0"})
        ET.SubElement(r, "mxCell", {"id": "1", "parent": "0"})
        return mx

    @classmethod
    def new(cls, width: int, height: int) -> "DiagramProject":
        mxfile = ET.Element(
            "mxfile",
            {
                "host": "drawio-studio",
                "agent": "drawio-studio/1.0.0",
                "modified": now_iso(),
                "version": "24.0.0",
                "type": "device",
            },
        )
        d = ET.SubElement(mxfile, "diagram", {"id": f"d_{uuid.uuid4().hex[:8]}", "name": "Page-1"})
        d.append(cls._base_mxgraph(width, height))
        return cls(mxfile)

    @classmethod
    def load(cls, path: Path) -> "DiagramProject":
        root = ET.fromstring(path.read_bytes())
        proj = cls(root, path)
        proj._normalize_diagrams()
        return proj

    def save(self, path: Path | None = None) -> Path:
        if path is not None:
            self.path = path
        if self.path is None:
            raise RuntimeError("No output path provided")
        ensure_parent(self.path)
        self.root.set("modified", now_iso())
        self.path.write_bytes(xml_bytes(self.root))
        return self.path

    def _normalize_diagrams(self) -> None:
        for d in self.diagrams():
            if d.find("mxGraphModel") is not None:
                continue
            txt = (d.text or "").strip()
            if not txt:
                continue
            try:
                gm = ET.fromstring(txt)
                d.text = None
                d.append(gm)
            except Exception:
                # leave untouched if unsupported encoding/compression
                pass

    def diagrams(self) -> list[ET.Element]:
        return [x for x in self.root.findall("diagram")]

    def get_page(self, idx: int) -> ET.Element:
        pages = self.diagrams()
        if idx < 0 or idx >= len(pages):
            raise IndexError(f"Invalid page index: {idx}")
        return pages[idx]

    def _mxgraph(self, idx: int) -> ET.Element:
        d = self.get_page(idx)
        gm = d.find("mxGraphModel")
        if gm is None:
            raise RuntimeError("Unsupported diagram encoding: mxGraphModel not found")
        return gm

    def _root_cell(self, idx: int) -> ET.Element:
        gm = self._mxgraph(idx)
        root_cell = gm.find("root")
        if root_cell is None:
            raise RuntimeError("Invalid diagram: root cell not found")
        return root_cell

    def _new_id(self, prefix: str = "v") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def _cells(self, idx: int) -> list[ET.Element]:
        return [c for c in self._root_cell(idx).findall("mxCell")]

    def _find_cell(self, idx: int, cell_id: str) -> ET.Element:
        for c in self._cells(idx):
            if c.get("id") == cell_id:
                return c
        raise ValueError(f"Cell not found: {cell_id}")

    def list_shapes(self, idx: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for c in self._cells(idx):
            if c.get("vertex") != "1":
                continue
            g = c.find("mxGeometry")
            out.append(
                {
                    "id": c.get("id"),
                    "label": c.get("value", ""),
                    "x": float(g.get("x", "0")) if g is not None else 0,
                    "y": float(g.get("y", "0")) if g is not None else 0,
                    "width": float(g.get("width", "0")) if g is not None else 0,
                    "height": float(g.get("height", "0")) if g is not None else 0,
                    "style": c.get("style", ""),
                }
            )
        return out

    def list_connectors(self, idx: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for c in self._cells(idx):
            if c.get("edge") != "1":
                continue
            out.append(
                {
                    "id": c.get("id"),
                    "label": c.get("value", ""),
                    "source": c.get("source"),
                    "target": c.get("target"),
                    "style": c.get("style", ""),
                }
            )
        return out

    def add_shape(
        self,
        idx: int,
        shape_type: str,
        label: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        if shape_type not in SHAPE_STYLES:
            raise ValueError(f"Unknown shape type: {shape_type}")
        cid = self._new_id("v")
        cell = ET.Element(
            "mxCell",
            {
                "id": cid,
                "value": label,
                "style": SHAPE_STYLES[shape_type],
                "vertex": "1",
                "parent": "1",
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "as": "geometry",
            },
        )
        self._root_cell(idx).append(cell)
        return {"id": cid, "shape_type": shape_type, "label": label, "x": x, "y": y, "width": width, "height": height}

    def remove_shape(self, idx: int, cell_id: str) -> dict[str, Any]:
        root = self._root_cell(idx)
        target = self._find_cell(idx, cell_id)
        if target.get("vertex") != "1":
            raise ValueError(f"Cell is not a shape: {cell_id}")
        # remove connected edges
        for c in list(root.findall("mxCell")):
            if c.get("edge") == "1" and (c.get("source") == cell_id or c.get("target") == cell_id):
                root.remove(c)
        root.remove(target)
        return {"id": cell_id, "removed": True}

    def update_label(self, idx: int, cell_id: str, label: str) -> dict[str, Any]:
        c = self._find_cell(idx, cell_id)
        c.set("value", label)
        return {"id": cell_id, "label": label}

    def move_shape(self, idx: int, cell_id: str, x: float, y: float) -> dict[str, Any]:
        c = self._find_cell(idx, cell_id)
        g = c.find("mxGeometry")
        if g is None:
            raise RuntimeError("mxGeometry missing")
        g.set("x", str(x))
        g.set("y", str(y))
        return {"id": cell_id, "x": x, "y": y}

    def resize_shape(self, idx: int, cell_id: str, w: float, h: float) -> dict[str, Any]:
        c = self._find_cell(idx, cell_id)
        g = c.find("mxGeometry")
        if g is None:
            raise RuntimeError("mxGeometry missing")
        g.set("width", str(w))
        g.set("height", str(h))
        return {"id": cell_id, "width": w, "height": h}

    @staticmethod
    def _set_style(style: str, key: str, value: str) -> str:
        tokens = [t for t in style.split(";") if t]
        found = False
        out: list[str] = []
        for t in tokens:
            if t.startswith(f"{key}="):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(t)
        if not found:
            out.append(f"{key}={value}")
        return ";".join(out) + ";"

    def style_cell(self, idx: int, cell_id: str, key: str, value: str) -> dict[str, Any]:
        c = self._find_cell(idx, cell_id)
        c.set("style", self._set_style(c.get("style", ""), key, value))
        return {"id": cell_id, "style": c.get("style", "")}

    def add_connector(
        self,
        idx: int,
        source_id: str,
        target_id: str,
        edge_style: str,
        label: str,
    ) -> dict[str, Any]:
        if edge_style not in EDGE_STYLES:
            raise ValueError(f"Unknown edge style: {edge_style}")
        self._find_cell(idx, source_id)
        self._find_cell(idx, target_id)
        cid = self._new_id("e")
        c = ET.Element(
            "mxCell",
            {
                "id": cid,
                "value": label,
                "style": EDGE_STYLES[edge_style],
                "edge": "1",
                "parent": "1",
                "source": source_id,
                "target": target_id,
            },
        )
        ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
        self._root_cell(idx).append(c)
        return {"id": cid, "source": source_id, "target": target_id, "style": edge_style, "label": label}

    def remove_connector(self, idx: int, edge_id: str) -> dict[str, Any]:
        root = self._root_cell(idx)
        c = self._find_cell(idx, edge_id)
        if c.get("edge") != "1":
            raise ValueError(f"Cell is not a connector: {edge_id}")
        root.remove(c)
        return {"id": edge_id, "removed": True}

    def add_page(self, name: str, width: int, height: int) -> dict[str, Any]:
        page_name = name or f"Page-{len(self.diagrams()) + 1}"
        d = ET.Element("diagram", {"id": f"d_{uuid.uuid4().hex[:8]}", "name": page_name})
        d.append(self._base_mxgraph(width, height))
        self.root.append(d)
        return {"index": len(self.diagrams()) - 1, "name": page_name, "width": width, "height": height}

    def remove_page(self, idx: int) -> dict[str, Any]:
        pages = self.diagrams()
        if len(pages) <= 1:
            raise ValueError("Cannot remove the last page")
        pg = self.get_page(idx)
        name = pg.get("name", f"Page-{idx}")
        self.root.remove(pg)
        return {"removed_index": idx, "name": name}

    def rename_page(self, idx: int, name: str) -> dict[str, Any]:
        pg = self.get_page(idx)
        pg.set("name", name)
        return {"index": idx, "name": name}

    def page_list(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i, d in enumerate(self.diagrams()):
            gm = d.find("mxGraphModel")
            w = gm.get("pageWidth") if gm is not None else None
            h = gm.get("pageHeight") if gm is not None else None
            out.append({"index": i, "id": d.get("id"), "name": d.get("name"), "width": w, "height": h})
        return out

    def info(self) -> dict[str, Any]:
        pages = self.page_list()
        shape_count = 0
        edge_count = 0
        for i in range(len(pages)):
            shape_count += len(self.list_shapes(i))
            edge_count += len(self.list_connectors(i))
        return {
            "path": str(self.path) if self.path else None,
            "pages": pages,
            "page_count": len(pages),
            "shape_count": shape_count,
            "connector_count": edge_count,
        }


def output(data: Any, as_json: bool = False, title: str | None = None) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if title:
        print(title)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)


def ensure_project_arg(project_path: str | None, session_meta: dict[str, Any]) -> Path:
    candidate = project_path or session_meta.get("project_path")
    if not candidate:
        raise SystemExit("No project specified. Use --project <file> or open/create one first.")
    p = Path(candidate).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"Project not found: {p}")
    return p


def save_and_snapshot(proj: DiagramProject, session: SessionStore, meta: dict[str, Any], path_override: Path | None = None) -> None:
    p = proj.save(path_override)
    meta["project_path"] = str(p)
    session.save(meta)
    session.record_snapshot(proj.root)


def run_repl(script_path: Path, session_id: str, project: str | None) -> int:
    print("Drawio Studio REPL. type 'quit' to exit.")
    while True:
        try:
            line = input("diagram> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line.lower() in {"quit", "exit", "q"}:
            return 0
        cmd = [sys.executable, str(script_path), "--session", session_id]
        if project:
            cmd += ["--project", project]
        cmd += shlex.split(line)
        subprocess.run(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Drawio Studio (no external code dependency)")
    parser.add_argument("--project", help="Path to .drawio file")
    parser.add_argument("--session", default="default", help="Session ID")
    parser.add_argument("--json", action="store_true", help="JSON output")

    sub = parser.add_subparsers(dest="group")

    # template
    p_tpl = sub.add_parser("template")
    tpl_sub = p_tpl.add_subparsers(dest="action")
    tpl_sub.add_parser("list")
    p_tc = tpl_sub.add_parser("create")
    p_tc.add_argument("--style", required=True, choices=["handdrawn", "clean", "dark-tech"])
    p_tc.add_argument("--output", required=True)
    p_tc.add_argument("--replacements")

    # project
    p_proj = sub.add_parser("project")
    pr_sub = p_proj.add_subparsers(dest="action")
    p_new = pr_sub.add_parser("new")
    p_new.add_argument("--preset", default="letter", choices=sorted(PAGE_PRESETS.keys()))
    p_new.add_argument("--width", type=int)
    p_new.add_argument("--height", type=int)
    p_new.add_argument("-o", "--output")
    p_open = pr_sub.add_parser("open")
    p_open.add_argument("path")
    p_save = pr_sub.add_parser("save")
    p_save.add_argument("path", nargs="?")
    pr_sub.add_parser("info")
    pr_sub.add_parser("xml")
    pr_sub.add_parser("presets")

    # shape
    p_shape = sub.add_parser("shape")
    sh_sub = p_shape.add_subparsers(dest="action")
    p_sa = sh_sub.add_parser("add")
    p_sa.add_argument("shape_type", nargs="?", default="rectangle", choices=sorted(SHAPE_STYLES.keys()))
    p_sa.add_argument("--label", "-l", default="")
    p_sa.add_argument("--x", type=float, default=100)
    p_sa.add_argument("--y", type=float, default=100)
    p_sa.add_argument("--width", "-w", type=float, default=120)
    p_sa.add_argument("--height", type=float, default=60)
    p_sa.add_argument("--page", type=int, default=0)

    p_sr = sh_sub.add_parser("remove")
    p_sr.add_argument("cell_id")
    p_sr.add_argument("--page", type=int, default=0)

    p_sl = sh_sub.add_parser("list")
    p_sl.add_argument("--page", type=int, default=0)

    p_slabel = sh_sub.add_parser("label")
    p_slabel.add_argument("cell_id")
    p_slabel.add_argument("label")
    p_slabel.add_argument("--page", type=int, default=0)

    p_sm = sh_sub.add_parser("move")
    p_sm.add_argument("cell_id")
    p_sm.add_argument("--x", required=True, type=float)
    p_sm.add_argument("--y", required=True, type=float)
    p_sm.add_argument("--page", type=int, default=0)

    p_ss = sh_sub.add_parser("resize")
    p_ss.add_argument("cell_id")
    p_ss.add_argument("--width", "-w", required=True, type=float)
    p_ss.add_argument("--height", required=True, type=float)
    p_ss.add_argument("--page", type=int, default=0)

    p_sst = sh_sub.add_parser("style")
    p_sst.add_argument("cell_id")
    p_sst.add_argument("key")
    p_sst.add_argument("value")
    p_sst.add_argument("--page", type=int, default=0)

    p_si = sh_sub.add_parser("info")
    p_si.add_argument("cell_id")
    p_si.add_argument("--page", type=int, default=0)

    sh_sub.add_parser("types")

    # connect
    p_conn = sub.add_parser("connect")
    c_sub = p_conn.add_subparsers(dest="action")
    p_ca = c_sub.add_parser("add")
    p_ca.add_argument("source_id")
    p_ca.add_argument("target_id")
    p_ca.add_argument("--style", default="orthogonal", choices=sorted(EDGE_STYLES.keys()))
    p_ca.add_argument("--label", "-l", default="")
    p_ca.add_argument("--page", type=int, default=0)

    p_cr = c_sub.add_parser("remove")
    p_cr.add_argument("edge_id")
    p_cr.add_argument("--page", type=int, default=0)

    p_cl = c_sub.add_parser("list")
    p_cl.add_argument("--page", type=int, default=0)

    p_clb = c_sub.add_parser("label")
    p_clb.add_argument("edge_id")
    p_clb.add_argument("label")
    p_clb.add_argument("--page", type=int, default=0)

    p_cst = c_sub.add_parser("style")
    p_cst.add_argument("edge_id")
    p_cst.add_argument("key")
    p_cst.add_argument("value")
    p_cst.add_argument("--page", type=int, default=0)

    c_sub.add_parser("styles")

    # page
    p_page = sub.add_parser("page")
    pg_sub = p_page.add_subparsers(dest="action")
    p_pa = pg_sub.add_parser("add")
    p_pa.add_argument("--name", default="")
    p_pa.add_argument("--width", type=int, default=850)
    p_pa.add_argument("--height", type=int, default=1100)

    p_pr = pg_sub.add_parser("remove")
    p_pr.add_argument("page_index", type=int)

    p_prn = pg_sub.add_parser("rename")
    p_prn.add_argument("page_index", type=int)
    p_prn.add_argument("name")

    pg_sub.add_parser("list")

    # export
    p_exp = sub.add_parser("export")
    ex_sub = p_exp.add_subparsers(dest="action")
    p_er = ex_sub.add_parser("render")
    p_er.add_argument("output_path")
    p_er.add_argument("-f", "--format", dest="fmt", default="png", choices=["png", "pdf", "svg", "vsdx", "xml", "drawio"])
    p_er.add_argument("--page", type=int)
    p_er.add_argument("--scale", type=float)
    p_er.add_argument("--width", type=int)
    p_er.add_argument("--height", type=int)
    p_er.add_argument("--transparent", action="store_true")
    p_er.add_argument("--crop", action="store_true")
    p_er.add_argument("--overwrite", action="store_true")
    ex_sub.add_parser("formats")

    # session
    p_sess = sub.add_parser("session")
    se_sub = p_sess.add_subparsers(dest="action")
    se_sub.add_parser("status")
    se_sub.add_parser("undo")
    se_sub.add_parser("redo")
    se_sub.add_parser("save-state")
    se_sub.add_parser("list")

    sub.add_parser("help-ops")
    sub.add_parser("repl")

    return parser


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".runtime" / "sessions"

    parser = build_parser()
    args = parser.parse_args()

    session = SessionStore(runtime, args.session)
    meta = session.load()

    try:
        if args.group == "help-ops":
            output(
                {
                    "groups": [
                        "template",
                        "project",
                        "shape",
                        "connect",
                        "page",
                        "export",
                        "session",
                        "repl",
                    ]
                },
                as_json=args.json,
                title="Operation groups",
            )
            return 0

        if args.group == "repl":
            return run_repl(Path(__file__), args.session, args.project or meta.get("project_path"))

        if args.group == "template":
            if args.action == "list":
                tdir = root / "assets" / "templates"
                output([x.name for x in sorted(tdir.glob("*.drawio"))], as_json=args.json)
                return 0
            if args.action == "create":
                style_map = {
                    "handdrawn": "architecture-handdrawn.drawio",
                    "clean": "architecture-clean.drawio",
                    "dark-tech": "architecture-dark-tech.drawio",
                }
                src = root / "assets" / "templates" / style_map[args.style]
                out = Path(args.output).expanduser().resolve()
                ensure_parent(out)
                content = src.read_text(encoding="utf-8")
                if args.replacements:
                    rep = json.loads(args.replacements)
                    for k, v in rep.items():
                        content = content.replace(str(k), str(v))
                out.write_text(content, encoding="utf-8")
                output({"output": str(out), "style": args.style}, as_json=args.json)
                return 0
            parser.error("template requires action")

        if args.group == "project":
            if args.action == "presets":
                data = {k: {"width": v[0], "height": v[1]} for k, v in PAGE_PRESETS.items()}
                output(data, as_json=args.json, title="Page presets")
                return 0

            if args.action == "new":
                w, h = PAGE_PRESETS[args.preset]
                if args.width:
                    w = args.width
                if args.height:
                    h = args.height
                proj = DiagramProject.new(w, h)
                out_path = Path(args.output).expanduser().resolve() if args.output else (runtime / args.session / "unsaved.drawio")
                saved = proj.save(out_path)
                meta = session.set_project(saved, proj.root)
                output({"action": "new_project", "page_size": f"{w}x{h}", "saved_to": str(saved)}, as_json=args.json)
                return 0

            if args.action == "open":
                p = Path(args.path).expanduser().resolve()
                if not p.exists():
                    raise SystemExit(f"File not found: {p}")
                proj = DiagramProject.load(p)
                meta = session.set_project(p, proj.root)
                output({"action": "open_project", "path": str(p), "page_count": len(proj.diagrams())}, as_json=args.json)
                return 0

            p = ensure_project_arg(args.project, meta)
            proj = DiagramProject.load(p)
            meta["project_path"] = str(p)
            session.save(meta)

            if args.action == "save":
                target = Path(args.path).expanduser().resolve() if args.path else p
                saved = proj.save(target)
                meta["project_path"] = str(saved)
                session.save(meta)
                session.record_snapshot(proj.root)
                output({"action": "save_project", "path": str(saved)}, as_json=args.json)
                return 0
            if args.action == "info":
                info = proj.info()
                output(info, as_json=args.json)
                return 0
            if args.action == "xml":
                print(xml_bytes(proj.root).decode("utf-8"))
                return 0
            parser.error("project requires action")

        if args.group in {"shape", "connect", "page", "export"}:
            p = ensure_project_arg(args.project, meta)
            proj = DiagramProject.load(p)
            meta["project_path"] = str(p)
            session.save(meta)

            if args.group == "shape":
                if args.action == "types":
                    output(sorted(SHAPE_STYLES.keys()), as_json=args.json)
                    return 0
                if args.action == "list":
                    output(proj.list_shapes(args.page), as_json=args.json)
                    return 0
                if args.action == "add":
                    res = proj.add_shape(args.page, args.shape_type, args.label, args.x, args.y, args.width, args.height)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "remove":
                    res = proj.remove_shape(args.page, args.cell_id)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "label":
                    res = proj.update_label(args.page, args.cell_id, args.label)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "move":
                    res = proj.move_shape(args.page, args.cell_id, args.x, args.y)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "resize":
                    res = proj.resize_shape(args.page, args.cell_id, args.width, args.height)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "style":
                    res = proj.style_cell(args.page, args.cell_id, args.key, args.value)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "info":
                    c = proj._find_cell(args.page, args.cell_id)
                    output(
                        {
                            "id": c.get("id"),
                            "label": c.get("value", ""),
                            "style": c.get("style", ""),
                            "vertex": c.get("vertex") == "1",
                            "edge": c.get("edge") == "1",
                            "source": c.get("source"),
                            "target": c.get("target"),
                        },
                        as_json=args.json,
                    )
                    return 0
                parser.error("shape requires action")

            if args.group == "connect":
                if args.action == "styles":
                    output(sorted(EDGE_STYLES.keys()), as_json=args.json)
                    return 0
                if args.action == "list":
                    output(proj.list_connectors(args.page), as_json=args.json)
                    return 0
                if args.action == "add":
                    res = proj.add_connector(args.page, args.source_id, args.target_id, args.style, args.label)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "remove":
                    res = proj.remove_connector(args.page, args.edge_id)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "label":
                    res = proj.update_label(args.page, args.edge_id, args.label)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "style":
                    res = proj.style_cell(args.page, args.edge_id, args.key, args.value)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                parser.error("connect requires action")

            if args.group == "page":
                if args.action == "list":
                    output(proj.page_list(), as_json=args.json)
                    return 0
                if args.action == "add":
                    res = proj.add_page(args.name, args.width, args.height)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "remove":
                    res = proj.remove_page(args.page_index)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                if args.action == "rename":
                    res = proj.rename_page(args.page_index, args.name)
                    save_and_snapshot(proj, session, meta)
                    output(res, as_json=args.json)
                    return 0
                parser.error("page requires action")

            if args.group == "export":
                if args.action == "formats":
                    output(["png", "pdf", "svg", "vsdx", "xml", "drawio"], as_json=args.json)
                    return 0
                if args.action == "render":
                    out = Path(args.output_path).expanduser().resolve()
                    if out.exists() and not args.overwrite:
                        raise SystemExit(f"Output exists. Use --overwrite: {out}")
                    ensure_parent(out)
                    proj.save(p)
                    if args.fmt in {"xml", "drawio"}:
                        out.write_bytes(xml_bytes(proj.root))
                        output({"output": str(out), "format": args.fmt, "mode": "direct"}, as_json=args.json)
                        return 0

                    drawio_bin = find_drawio_bin()
                    if not drawio_bin:
                        raise SystemExit(
                            "Export to image/pdf requires local draw.io desktop binary. "
                            "Install draw.io or set DRAWIO_STUDIO_DRAWIO_BIN."
                        )

                    cmd = [
                        drawio_bin,
                        "--export",
                        str(p),
                        "--output",
                        str(out),
                        "--format",
                        args.fmt,
                        "--overwrite",
                    ]
                    if args.page is not None:
                        cmd += ["--page-index", str(args.page)]
                    if args.scale is not None:
                        cmd += ["--scale", str(args.scale)]
                    if args.width is not None:
                        cmd += ["--width", str(args.width)]
                    if args.height is not None:
                        cmd += ["--height", str(args.height)]
                    if args.transparent:
                        cmd += ["--transparent"]
                    if args.crop:
                        cmd += ["--crop"]

                    cp = subprocess.run(cmd, check=False)
                    if cp.returncode != 0:
                        raise SystemExit(f"draw.io export failed (code {cp.returncode})")
                    output({"output": str(out), "format": args.fmt, "engine": "local-drawio"}, as_json=args.json)
                    return 0
                parser.error("export requires action")

        if args.group == "session":
            if args.action == "status":
                meta = session.load()
                output(meta, as_json=args.json)
                return 0
            if args.action == "save-state":
                meta = session.load()
                session.save(meta)
                output({"saved": True, "session": args.session, "meta": str(session.meta_path)}, as_json=args.json)
                return 0
            if args.action == "list":
                sessions = []
                runtime.mkdir(parents=True, exist_ok=True)
                for d in sorted([x for x in runtime.iterdir() if x.is_dir()]):
                    mp = d / "metadata.json"
                    if mp.exists():
                        data = json.loads(mp.read_text(encoding="utf-8"))
                        sessions.append({"session_id": d.name, "project_path": data.get("project_path"), "updated_at": data.get("updated_at")})
                output(sessions, as_json=args.json)
                return 0
            if args.action in {"undo", "redo"}:
                meta = session.load()
                project_path = meta.get("project_path")
                if not project_path:
                    raise SystemExit("No active project in session")
                p = Path(project_path)
                res = session.undo() if args.action == "undo" else session.redo()
                if res is None:
                    output({"action": args.action, "success": False, "message": f"Nothing to {args.action}"}, as_json=args.json)
                    return 0
                m2, snapshot_root = res
                p.write_bytes(xml_bytes(snapshot_root))
                output({"action": args.action, "success": True, "project_path": str(p), "index": m2.get("index")}, as_json=args.json)
                return 0
            parser.error("session requires action")

        parser.print_help()
        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "type": type(e).__name__}, ensure_ascii=False))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
