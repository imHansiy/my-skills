"""探测一个尚未封装的 action 是否可用。

用法：
    python scripts/probe_action.py getSomeAction '{"param1": "x"}'
    python scripts/probe_action.py listFile '{"parentFileId": "root", "limit": 5}' --endpoint /aliyundrive/request

只打印脱敏后的结果摘要（不打印 cookie / ticket）。
退出码 0 = 服务端返回 code:"0" 或 success:true，可以封装。
"""

from __future__ import annotations

import argparse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SDK = r"D:\Dev\Anything Analyzer\tingwu-python"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", help="要探测的 action 名")
    ap.add_argument("params", nargs="?", default="{}", help="JSON 参数")
    ap.add_argument("--endpoint", default=None, help="覆盖 endpoint，如 /export/request")
    ap.add_argument("--sdk", default=SDK, help="SDK 路径")
    ap.add_argument("--show", type=int, default=600, help="打印响应前 N 字符")
    args = ap.parse_args()

    sys.path.insert(0, args.sdk)
    try:
        from tingwu import TingwuClient, Ticket
    except ImportError as e:
        print(f"导入失败：{e}\n先 pip install -e \"{args.sdk}\"")
        return 2

    try:
        params = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError as e:
        print(f"params 不是合法 JSON：{e}")
        return 2

    c = TingwuClient(ticket=Ticket.load().value)
    if not c.check():
        print("登录态失效，先重新获取 ticket（见 references/AUTH.md）")
        return 1

    try:
        res = c.request(args.action, params=params, endpoint=args.endpoint, raw=True)
    except Exception as e:  # APIError 等
        print(f"FAILED  {type(e).__name__}: {e}")
        return 1

    text = json.dumps(res, ensure_ascii=False)
    print(f"OK  {text[: args.show]}")
    ok = res.get("success") is True or str(res.get("code")) == "0"
    print("---")
    print("结论：可以封装" if ok else "结论：不要封装（响应不是成功）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
