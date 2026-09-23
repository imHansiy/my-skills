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

    def create(
        self, dir_name: str, *, parent_dir_id: int = -1, raw: bool = False, **extra: Any
    ) -> Any:
        """新建文件夹。

        Args:
            dir_name: 文件夹名。
            parent_dir_id: 父文件夹 ID；``-1``（默认）= 建在根目录。
            raw: True 返回完整响应（含 ``code``）。

        Returns:
            默认返回 ``data``：``{"focusDir": {...新建的那项...},
            "dirList": [...完整目录树...]}``。要从 ``focusDir.dirId`` 取新 ID。
        """
        res = self._c.request(
            "addDir",
            params={
                "dirName": dir_name,
                "parentDirId": parent_dir_id,
                "returnNewList": 1,
                **extra,
            },
            raw=True,
        )
        return res if raw else res.get("data", res)
    def rename(self, dir_id: int, new_name: str, *, raw: bool = False) -> Any:
        """重命名文件夹。

        Args:
            raw: True 返回完整响应（含 ``code``）。默认返回 ``data``——
                带 ``returnNewList`` 时是**新的完整目录列表**（前端靠它
                刷新树），不带时 ``data`` 为 ``None``（但改名已生效）。
        """
        res = self._c.request(
            "updateDir",
            params={"dirId": dir_id, "dirName": new_name, "returnNewList": 1},
            raw=True,
        )
        return res if raw else res.get("data", res)

    def delete(self, dir_id: int, *, raw: bool = False) -> Any:
        """删除文件夹（其下记录会同步删除，前端有二次确认弹窗）。

        Note:
            删除前建议先用 :meth:`has_processing` 确认没有进行中的转写任务；
            有的话任务会转入默认文件夹。
        """
        res = self._c.request(
            "delDir", params={"dirId": dir_id, "returnNewList": 1}, raw=True
        )
        return res if raw else res.get("data", res)

    def move_trans(
        self, trans_ids: "int | str | list", dest_dir_id: int, *, raw: bool = False
    ) -> Any:
        """把**转写记录**移动到目标文件夹。

        Args:
            trans_ids: 记录 ID，或 ID 列表。
            dest_dir_id: 目标文件夹 ID（``0`` = 默认文件夹）。

        Note:
            参数是 ``destDirId`` + ``transIds``（**不是** ``targetDirId`` /
            ``dirIds``，也不是单数 ``transId``——后两种实测都返回
            ``CMN.ServerError``）。移动的是记录，文件夹本身不能这样移动。
        """
        ids = [trans_ids] if isinstance(trans_ids, (int, str)) else list(trans_ids)
        res = self._c.request(
            "changeDir", params={"destDirId": dest_dir_id, "transIds": ids}, raw=True
        )
        return res if raw else res.get("data", res)

    def has_processing(self, dir_id: int) -> bool:
        """该目录下是否有进行中的转写任务。

        Note:
            ``dirId=0``（默认文件夹）会返回 ``DIR.InvalidRequest``；
            只对真实文件夹 ID 调用。返回值在 ``data.existProcessingTrans``。
        """
        res = self._c.request(
            "existProcessingTrans", params={"dirId": dir_id}, raw=True
        )
        data = res.get("data") or {}
        return bool(data.get("existProcessingTrans"))
