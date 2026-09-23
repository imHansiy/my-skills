"""文件夹（目录）接口。"""

from __future__ import annotations

from typing import Any, Optional


class DirectoryResource:
    """文件夹树管理。

    听悟的目录树：``dirId=0`` 是"默认文件夹"，根节点 ``parentDirId=-1``。
    """

    def __init__(self, client: Any) -> None:
        self._c = client

    def list(self, *, return_details: bool = True) -> list[dict[str, Any]]:
        """取完整目录树（嵌套 ``children``）。"""
        return self._c.request("getDirList", params={"returnDetails": return_details})

    def tree(self) -> list[dict[str, Any]]:
        """:meth:`list` 的别名，语义更直观。"""
        return self.list()

    def flatten(self) -> list[dict[str, Any]]:
        """把目录树拍平成列表，每项附带 ``path``（如 ``工作/odoo/winston``）。"""
        out: list[dict[str, Any]] = []

        def walk(nodes: list[dict[str, Any]], prefix: str) -> None:
            for n in nodes:
                name = n.get("dirName", "")
                path = f"{prefix}/{name}" if prefix else name
                item = dict(n)
                item["path"] = path
                item.pop("children", None)
                out.append(item)
                walk(n.get("children") or [], path)

        walk(self.list(), "")
        return out

    def find_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """按名称找文件夹（返回第一个匹配）。"""
        for d in self.flatten():
            if d.get("dirName") == name:
                return d
        return None

    def create(self, dir_name: str, *, parent_dir_id: int = -1, **extra: Any) -> Any:
        """新建文件夹。"""
        return self._c.request(
            "addDir",
            params={"dirName": dir_name, "parentDirId": parent_dir_id, "returnNewList": 1, **extra},
        )

    def rename(self, dir_id: int, new_name: str) -> Any:
        """重命名文件夹。"""
        return self._c.request("updateDir", params={"dirId": dir_id, "dirName": new_name})

    def delete(self, dir_id: int) -> Any:
        """删除文件夹。"""
        return self._c.request("delDir", params={"dirId": dir_id})

    def move(self, dir_ids: "int | list[int]", target_dir_id: int) -> Any:
        """移动文件夹/文件到目标目录。"""
        ids = [dir_ids] if isinstance(dir_ids, int) else list(dir_ids)
        return self._c.request(
            "changeDir", params={"dirIds": ids, "targetDirId": target_dir_id}
        )

    def has_processing(self, dir_id: int) -> bool:
        """该目录下是否有进行中的任务。"""
        res = self._c.request("existProcessingTrans", params={"dirId": dir_id})
        return bool(res)
