"""订阅、权益（签到/时长）接口。"""

from __future__ import annotations

from typing import Any, Optional


class SubscriptionResource:
    """权益、签到、推广活动。

    时长单位是秒。``timeFlow`` 为已用，``maxTimeFlow`` 为上限。
    """

    def __init__(self, client: Any) -> None:
        self._c = client

    def gain_daily(self) -> dict[str, Any]:
        """领取每日签到权益（幂等，重复调用返回 ``isAlreadyGain: true``）。

        Returns:
            服务端原始字段，含 ``timeFlow``、``maxTimeFlow``、``count``（连续签到天数）、
            ``isAlreadyGain``、``exceedMaxTimeFlow`` 等。

        Note:
            ``timeFlow`` 的语义**未经证实**：实测签到后它仍为 ``0``，
            而 ``maxTimeFlow`` 为 ``1440000``（400 小时）。它可能是
            "今日获得/消耗"而非"剩余可用"。需要剩余时长请以客户端展示为准，
            或自行抓包确认后再使用 :meth:`remaining_seconds`。
        """
        return self._c.direct(
            "gain_equity",
            body={"equityType": "daily_sign_in", "equityCode": "every_day"},
        )

    def sign_in_days(self) -> Optional[int]:
        """连续签到天数。"""
        v = self.gain_daily().get("count")
        return int(v) if v is not None else None

    def max_time_flow_hours(self) -> Optional[float]:
        """时长上限（小时）。``maxTimeFlow`` 单位是秒。"""
        v = self.gain_daily().get("maxTimeFlow")
        return int(v) / 3600.0 if v is not None else None

    def remaining_seconds(self) -> Optional[int]:
        """剩余可用时长（秒）。

        Warning:
            ``timeFlow`` 语义未证实（见 :meth:`gain_daily`）。
            该方法只是把 ``timeFlow`` 按秒返回，使用前请自行验证。
        """
        v = self.gain_daily().get("timeFlow")
        return int(v) if v is not None else None

    def remaining_hours(self) -> Optional[float]:
        """剩余可用时长（小时）。语义未证实，见 :meth:`remaining_seconds`。"""
        s = self.remaining_seconds()
        return s / 3600.0 if s is not None else None

    def login_warning(self) -> Any:
        """登录时长预警（前端每次登录调用）。"""
        return self._c.direct("login_warning", body={})

    def aliyundrive_equity_status(self) -> Any:
        """阿里云盘权益状态。"""
        return self._c.direct("equity_status_v2", method="GET")

    def bring_new_user_ranking(self) -> Any:
        """邀请排行。"""
        return self._c.direct("bring_new_user_ranking")

    def promotion_status(self, codes: "list[str] | None" = None) -> Any:
        """推广活动状态（如教育认证）。"""
        return self._c.direct(
            "promotion_status",
            body={"codeFilter": codes or ["education_certification"]},
        )

    def sync_promotion_tip(self, **params: Any) -> Any:
        """同步推广提示状态。"""
        return self._c.direct("sync_promotion_tip", body=params)

    def user_summary(self, **params: Any) -> Any:
        """用户每日权益汇总。"""
        return self._c.request("getUserSummaryDayEquity", params=params)
