from __future__ import annotations

import textwrap
import threading

from smart_mirror.data.alarm import AlarmData
from smart_mirror.data.location import LocationData
from smart_mirror.data.weather import WeatherData
from smart_mirror.display.display_adapter import DisplayAdapter
from smart_mirror.display.screen_state import ScreenState

# ── Размеры экрана ───────────────────────────────────────────────────────────
_W = 160
_H = 128

# ── Цвета ────────────────────────────────────────────────────────────────────
_BG             = "black"
_C_TIME         = "white"
_C_CITY         = "#888888"
_C_WEATHER_DESC = "cyan"
_C_WEATHER_DET  = "#cccccc"
_C_PHRASE       = "#ffff66"
_C_ALARM        = "#66ff66"
_C_ALARM_BG     = "#330000"
_C_ALARM_TEXT   = "#ff4444"
_C_SEP          = "#333333"

# ── Шрифты ───────────────────────────────────────────────────────────────────
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Количество символов в строке для переноса фразы (10px шрифт, ~6px/символ)
_PHRASE_WRAP_COLS = 26


def _load_fonts() -> dict:
    from PIL import ImageFont
    try:
        return {
            "time":   ImageFont.truetype(_FONT_BOLD, 20),
            "normal": ImageFont.truetype(_FONT_REG,  10),
            "bold":   ImageFont.truetype(_FONT_BOLD, 10),
            "alert":  ImageFont.truetype(_FONT_BOLD, 12),
        }
    except OSError:
        # Нет DejaVu (не Pi) — используем встроенный растровый шрифт
        fallback = ImageFont.load_default()
        return {k: fallback for k in ("time", "normal", "bold", "alert")}


class St7735Display(DisplayAdapter):
    """
    Реализация DisplayAdapter для ST7735 TFT 1.8" (160×128).

    Инициализация SPI:
      DC  → GPIO25  (Pin 22)
      RST → GPIO24  (Pin 18)
      CS  → GPIO8   (Pin 24, CE0)
    """

    def __init__(self) -> None:
        self._state = ScreenState()
        self._state_lock = threading.Lock()   # защищает self._state
        self._render_lock = threading.Lock()  # сериализует SPI-передачи
        self._device = _init_device()
        self._fonts = _load_fonts()

    # ── DisplayAdapter API ───────────────────────────────────────────────────

    def update_time(self, time_str: str) -> None:
        with self._state_lock:
            self._state.current_time = time_str
            self._state.alarm_triggered = False
        self.render()

    def update_weather(self, data: WeatherData) -> None:
        with self._state_lock:
            self._state.weather = data
        self.render()

    def update_phrase(self, phrase: str) -> None:
        with self._state_lock:
            self._state.phrase = phrase
        self.render()

    def update_alarm(self, alarm: AlarmData | None) -> None:
        with self._state_lock:
            self._state.alarm = alarm
        self.render()

    def update_location(self, location: LocationData | None) -> None:
        with self._state_lock:
            self._state.location = location
        self.render()

    def show_alarm_triggered(self) -> None:
        with self._state_lock:
            self._state.alarm_triggered = True
        self.render()

    def dismiss_alarm_triggered(self) -> None:
        with self._state_lock:
            self._state.alarm_triggered = False
        self.render()

    def render(self) -> None:
        # Снимаем снапшот состояния под коротким локом
        with self._state_lock:
            s = ScreenState(
                current_time=self._state.current_time,
                weather=self._state.weather,
                phrase=self._state.phrase,
                alarm=self._state.alarm,
                alarm_triggered=self._state.alarm_triggered,
                location=self._state.location,
            )

        # Рисуем и передаём на дисплей под render-локом (один SPI за раз)
        with self._render_lock:
            img = _draw_screen(s, self._fonts)
            self._device.display(img)


# ── Инициализация устройства ─────────────────────────────────────────────────

def _init_device():
    from luma.core.interface.serial import spi
    from luma.lcd.device import st7735

    serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24)
    return st7735(serial, width=_W, height=_H, bgr=True)


# ── Отрисовка экрана ─────────────────────────────────────────────────────────

def _draw_screen(s: ScreenState, fonts: dict):
    from PIL import Image, ImageDraw

    img  = Image.new("RGB", (_W, _H), _BG)
    draw = ImageDraw.Draw(img)
    y    = 4

    # ── Время ────────────────────────────────────────────────────────────────
    time_str = s.current_time or "--:--"
    draw.text((4, y), time_str, fill=_C_TIME, font=fonts["time"])
    y += 24

    # ── Город (справа от времени, на той же строке) ──────────────────────────
    if s.location and s.location.city:
        draw.text((4, y), s.location.city, fill=_C_CITY, font=fonts["normal"])
    y += 13

    # ── Разделитель ──────────────────────────────────────────────────────────
    y = _sep(draw, y)

    # ── Погода ───────────────────────────────────────────────────────────────
    if s.weather:
        draw.text((4, y), s.weather.description, fill=_C_WEATHER_DESC, font=fonts["normal"])
        y += 13
        detail = f"{s.weather.temperature_celsius:.1f}°C   {s.weather.wind_speed_kmh:.0f} км/ч"
        draw.text((4, y), detail, fill=_C_WEATHER_DET, font=fonts["normal"])
        y += 13
    else:
        y += 13  # резервируем место, чтобы макет не прыгал

    # ── Разделитель ──────────────────────────────────────────────────────────
    y = _sep(draw, y)

    # ── Фраза (до 2 строк) ───────────────────────────────────────────────────
    if s.phrase:
        for line in textwrap.wrap(s.phrase, width=_PHRASE_WRAP_COLS)[:2]:
            draw.text((4, y), line, fill=_C_PHRASE, font=fonts["normal"])
            y += 13

    # ── Будильник ────────────────────────────────────────────────────────────
    if s.alarm:
        y = _sep(draw, y)
        draw.text((4, y), f"Будильник: {s.alarm}", fill=_C_ALARM, font=fonts["bold"])
        y += 13

    # ── Баннер БУДИЛЬНИК СРАБОТАЛ ────────────────────────────────────────────
    if s.alarm_triggered:
        by = _H - 28
        draw.rectangle([(0, by), (_W, _H)], fill=_C_ALARM_BG)
        draw.text((4, by + 6), "!!! ПРОСЫПАЙСЯ !!!", fill=_C_ALARM_TEXT, font=fonts["alert"])

    return img


def _sep(draw, y: int) -> int:
    """Рисует горизонтальный разделитель и возвращает y после него."""
    draw.line([(0, y), (_W, y)], fill=_C_SEP)
    return y + 4
