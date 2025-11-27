# CREATED_BY_AGENT
"""同步 FastAPI 路由上的 NOT_USED 标签。

根据 `app/api/used_api_endpoints.py` 中的真实流量快照，
为所有未被使用的接口追加 `NOT_USED` tag，便于调试与清理。
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

import libcst as cst

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.used_api_endpoints import USED_API_ENDPOINT_PATHS  # noqa: E402


def _literal_string(node: cst.CSTNode | None) -> Optional[str]:
    if isinstance(node, cst.SimpleString):
        try:
            return ast.literal_eval(node.value)
        except Exception:  # pragma: no cover - 解析失败直接忽略
            return None
    return None


def _combine_paths(api_prefix: str, router_prefix: str, route_path: str) -> str:
    parts = [api_prefix or "", router_prefix or "", route_path or ""]
    result = ""
    for part in parts:
        if not part:
            continue
        if part == "/":
            result = (result.rstrip("/") if result else "") + "/"
            continue
        if not result:
            result = part if part.startswith("/") else f"/{part}"
            continue
        result = result.rstrip("/")
        normalized = part if part.startswith("/") else f"/{part}"
        result += normalized
    return result or "/"


def _module_name(module: cst.BaseExpression | None) -> Optional[str]:
    if module is None:
        return None
    if isinstance(module, cst.Name):
        return module.value

    parts: List[str] = []
    current = module
    while isinstance(current, cst.Attribute):
        parts.append(current.attr.value)
        current = current.value
    if isinstance(current, cst.Name):
        parts.append(current.value)
        return ".".join(reversed(parts))
    return None


def _build_attr(dotted: str) -> cst.BaseExpression:
    parts = dotted.split(".")
    expr: cst.BaseExpression = cst.Name(parts[0])
    for part in parts[1:]:
        expr = cst.Attribute(value=expr, attr=cst.Name(part))
    return expr


def _is_docstring(stmt: cst.CSTNode) -> bool:
    if not isinstance(stmt, cst.SimpleStatementLine):
        return False
    if len(stmt.body) != 1:
        return False
    expr = stmt.body[0]
    return isinstance(expr, cst.Expr) and isinstance(expr.value, cst.SimpleString)


def _is_import_stmt(stmt: cst.CSTNode) -> bool:
    if not isinstance(stmt, cst.SimpleStatementLine):
        return False
    if not stmt.body:
        return False
    return isinstance(
        stmt.body[0],
        (
            cst.Import,
            cst.ImportFrom,
        ),
    )


def _insertion_index(body: Sequence[cst.CSTNode]) -> int:
    index = 0
    for idx, stmt in enumerate(body):
        if _is_docstring(stmt) or _is_import_stmt(stmt):
            index = idx + 1
        else:
            break
    return index


@dataclass
class RouterInfo:
    prefix: str


class RouterCollector(cst.CSTVisitor):
    def __init__(self) -> None:
        self.prefixes: Dict[str, RouterInfo] = {}

    def visit_Assign(self, node: cst.Assign) -> None:
        if len(node.targets) != 1:
            return
        target = node.targets[0].target
        if not isinstance(target, cst.Name):
            return
        if not isinstance(node.value, cst.Call):
            return
        func = node.value.func
        if not isinstance(func, cst.Name) or func.value != "APIRouter":
            return

        prefix = ""
        for arg in node.value.args:
            if arg.keyword and arg.keyword.value == "prefix":
                prefix = _literal_string(arg.value) or ""
                break

        self.prefixes[target.value] = RouterInfo(prefix=prefix)


class RouteTagTransformer(cst.CSTTransformer):
    def __init__(
        self,
        *,
        router_prefixes: Mapping[str, RouterInfo],
        api_prefix: str,
        used_paths: Set[str],
    ) -> None:
        self.router_prefixes = router_prefixes
        self.api_prefix = api_prefix
        self.used_paths = used_paths
        self.modified = False
        self.has_not_used_reference = False
        self.has_tags_import = False
        self.tags_import_has_not_used = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module_name = _module_name(node.module)
        if module_name == "app.api.tags":
            self.has_tags_import = True
            if isinstance(node.names, Sequence):
                for alias in node.names:
                    if isinstance(alias, cst.ImportAlias) and isinstance(
                        alias.name, cst.Name
                    ):
                        if alias.name.value == "NOT_USED_TAG":
                            self.tags_import_has_not_used = True
                            break

    def leave_Decorator(
        self, original_node: cst.Decorator, updated_node: cst.Decorator
    ) -> cst.Decorator:
        decorator = updated_node.decorator
        if not isinstance(decorator, cst.Call):
            return updated_node

        func = decorator.func
        if not isinstance(func, cst.Attribute):
            return updated_node
        if not isinstance(func.value, cst.Name):
            return updated_node

        router_name = func.value.value
        router = self.router_prefixes.get(router_name)
        if router is None:
            return updated_node

        path_arg = None
        for arg in decorator.args:
            if arg.keyword is None:
                path_arg = arg
                break

        route_path = _literal_string(path_arg.value) if path_arg else ""
        if route_path is None:
            return updated_node

        full_path = _combine_paths(self.api_prefix, router.prefix, route_path)
        if full_path in self.used_paths:
            return updated_node

        new_call = self._ensure_not_used_tag(decorator)
        if new_call is None:
            return updated_node

        self.modified = True
        self.has_not_used_reference = True
        return updated_node.with_changes(decorator=new_call)

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self.has_not_used_reference:
            body: List[cst.CSTNode] = list(updated_node.body)
            if self.has_tags_import and not self.tags_import_has_not_used:
                new_body: List[cst.CSTNode] = []
                appended = False
                for stmt in body:
                    if (
                        not appended
                        and isinstance(stmt, cst.SimpleStatementLine)
                        and stmt.body
                        and isinstance(stmt.body[0], cst.ImportFrom)
                        and _module_name(stmt.body[0].module) == "app.api.tags"
                        and isinstance(stmt.body[0].names, Sequence)
                    ):
                        import_from = stmt.body[0]
                        names = list(import_from.names)
                        names.append(cst.ImportAlias(name=cst.Name("NOT_USED_TAG")))
                        new_import = import_from.with_changes(names=names)
                        stmt = stmt.with_changes(body=[new_import])
                        appended = True
                        self.tags_import_has_not_used = True
                        self.modified = True
                    new_body.append(stmt)
                body = new_body
            elif not self.has_tags_import:
                new_import = cst.SimpleStatementLine(
                    body=[
                        cst.ImportFrom(
                            module=_build_attr("app.api.tags"),
                            names=[cst.ImportAlias(name=cst.Name("NOT_USED_TAG"))],
                        )
                    ]
                )
                insert_at = _insertion_index(body)
                body.insert(insert_at, new_import)
                self.modified = True
            updated_node = updated_node.with_changes(body=body)
        return updated_node

    def _ensure_not_used_tag(self, call: cst.Call) -> Optional[cst.Call]:
        tags_index = None
        for idx, arg in enumerate(call.args):
            if arg.keyword and arg.keyword.value == "tags":
                tags_index = idx
                break

        args: List[cst.Arg] = list(call.args)
        if tags_index is None:
            whitespace = (
                call.args[-1].whitespace_before_arg
                if call.args
                else cst.SimpleWhitespace("\n    ")
            )
            new_list = cst.List(
                [cst.Element(cst.Name("NOT_USED_TAG"))],
                lbracket=cst.LeftSquareBracket(),
                rbracket=cst.RightSquareBracket(),
            )
            args.append(
                cst.Arg(
                    keyword=cst.Name("tags"),
                    value=new_list,
                    whitespace_before_arg=whitespace,
                    equal=cst.AssignEqual(
                        whitespace_before=cst.SimpleWhitespace(""),
                        whitespace_after=cst.SimpleWhitespace(""),
                    ),
                )
            )
            return call.with_changes(args=args)

        tags_arg = args[tags_index]
        value = tags_arg.value

        if isinstance(value, cst.List):
            if self._list_has_not_used(value.elements):
                return None
            new_elements = list(value.elements)
            new_elements.append(cst.Element(cst.Name("NOT_USED_TAG")))
            args[tags_index] = tags_arg.with_changes(
                value=value.with_changes(elements=new_elements)
            )
            self.has_not_used_reference = True
            return call.with_changes(args=args)

        if isinstance(value, cst.Tuple):
            if self._list_has_not_used(value.elements):
                return None
            new_list = cst.List(
                elements=[
                    cst.Element(element.value) for element in value.elements
                ]
                + [cst.Element(cst.Name("NOT_USED_TAG"))]
            )
            args[tags_index] = tags_arg.with_changes(value=new_list)
            self.has_not_used_reference = True
            return call.with_changes(args=args)

        new_list = cst.List(
            elements=[
                cst.Element(value),
                cst.Element(cst.Name("NOT_USED_TAG")),
            ]
        )
        args[tags_index] = tags_arg.with_changes(value=new_list)
        self.has_not_used_reference = True
        return call.with_changes(args=args)

    def _list_has_not_used(self, elements: Sequence[cst.Element]) -> bool:
        for element in elements:
            node = element.value
            if isinstance(node, cst.Name) and node.value == "NOT_USED_TAG":
                self.has_not_used_reference = True
                return True
            if isinstance(node, cst.SimpleString):
                try:
                    if ast.literal_eval(node.value) == "NOT_USED":
                        self.has_not_used_reference = True
                        return True
                except Exception:
                    continue
        return False


def _api_prefix_for(path: Path) -> str:
    posix = path.as_posix()
    if "/api/v1/" in posix:
        return "/api/v1"
    if "/api/v2/" in posix:
        return "/api/v2"
    raise ValueError(f"未知的 API 版本（仅支持 v1/v2）: {path}")


def _iter_endpoint_files() -> Iterable[Path]:
    for version in ("v1", "v2"):
        directory = ROOT_DIR / "app" / "api" / version / "endpoints"
        if not directory.exists():
            continue
        yield from sorted(directory.glob("*.py"))


def process_file(path: Path) -> bool:
    api_prefix = _api_prefix_for(path)
    source = path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    collector = RouterCollector()
    module.visit(collector)
    transformer = RouteTagTransformer(
        router_prefixes=collector.prefixes,
        api_prefix=api_prefix,
        used_paths=set(USED_API_ENDPOINT_PATHS),
    )
    updated_module = module.visit(transformer)
    if transformer.modified:
        path.write_text(updated_module.code, encoding="utf-8")
    return transformer.modified


def main() -> None:
    parser = argparse.ArgumentParser(description="同步 NOT_USED 标签")
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅检查是否需要更新，若存在差异则退出码为 1",
    )
    args = parser.parse_args()

    changed_files: List[Path] = []
    for file_path in _iter_endpoint_files():
        if process_file(file_path):
            changed_files.append(file_path)

    if args.check and changed_files:
        print("需要同步 NOT_USED 标签的文件：")
        for path in changed_files:
            print(f"- {path.relative_to(ROOT_DIR)}")
        raise SystemExit(1)

    if changed_files:
        print("已更新以下文件的 NOT_USED 标签：")
        for path in changed_files:
            print(f"- {path.relative_to(ROOT_DIR)}")
    else:
        print("所有 FastAPI 路由的 NOT_USED 标签均已同步。")


if __name__ == "__main__":
    main()
