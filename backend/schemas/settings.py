from __future__ import annotations

from pydantic import BaseModel


class GeneralSettingsResponse(BaseModel):
    username: str = ""
    auto_refresh_minutes: int = 5
    max_home_tasks: int = 10
    language: str = "fr"
    enabled_modules: dict = {}
    card_order: list = []
    card_layout: list = []
    show_alert_ws: bool = True
    show_alert_warranty: bool = True


class ThemeSettingsResponse(BaseModel):
    theme: str = "glass"
    accent: str = "#06A6C9"
    brand_icon: str = "\u26a1"
