#!/usr/bin/env python3
"""
test_hardware.py — Проверка компонентов умного зеркала.

Этот скрипт НЕ является частью основного приложения.
Запускай его на Raspberry Pi, чтобы убедиться, что железо подключено правильно.

Компоненты:
  - ST7735 TFT SPI 1.8" (128 x 160 пикселей)
  - TTP223 ёмкостная сенсорная кнопка
  - KY-012 активный зуммер

Распиновка (из документации проекта):
  ST7735 │ Raspberry Pi
  ───────┼─────────────────────────────
  VCC    │ 3.3V  (Pin 1)
  GND    │ GND   (Pin 6)
  SCL    │ GPIO11 / SCLK (Pin 23)
  SDA    │ GPIO10 / MOSI (Pin 19)
  RES    │ GPIO24        (Pin 18)
  DC     │ GPIO25        (Pin 22)
  CS     │ GPIO8  / CE0  (Pin 24)
  BL/LED │ 3.3V  (Pin 1 или 17)

  TTP223 │ Raspberry Pi
  ───────┼─────────────
  VCC    │ 3.3V
  GND    │ GND
  OUT    │ GPIO17

  KY-012 │ Raspberry Pi
  ───────┼─────────────
  S      │ GPIO19
  +      │ 3.3V
  -      │ GND

Установка зависимостей:
  .venv/bin/pip install -r requirements.txt

Включение SPI на Pi (если ещё не включено):
  sudo raspi-config → Interface Options → SPI → Enable → Reboot

Запуск (через run.sh, он передаёт venv-интерпретатор в sudo):
  ./run.sh test_hardware.py

Почему нельзя просто "sudo python3 test_hardware.py":
  sudo использует системный Python, который не видит пакеты из venv.
  run.sh передаёт sudo полный путь к venv/bin/python3 — проблема решена.
"""

import sys
import time

# ─── Пины ────────────────────────────────────────────────────────────────────
PIN_TOUCH = 17    # TTP223 — вывод OUT
PIN_BUZZER = 19   # KY-012 — вывод S

# ST7735 — SPI0: CLK=GPIO11, MOSI=GPIO10, CS=GPIO8, DC=GPIO25, RES=GPIO24
# (настраивается через luma.lcd ниже)

# ─── Параметры теста ─────────────────────────────────────────────────────────
BUZZER_BEEP_DURATION = 0.15   # сек — длительность одного сигнала
BUZZER_PAUSE = 0.1            # сек — пауза между сигналами
TOUCH_WAIT_TIMEOUT = 15       # сек — сколько ждём нажатия кнопки


# ─── Тест: ST7735 дисплей ─────────────────────────────────────────────────────

def test_display() -> bool:
    """
    Инициализирует ST7735 через SPI и рисует:
      1) Цветные полосы (проверка всех каналов RGB)
      2) Текст (проверка вывода символов)
    Возвращает True при успехе.
    """
    try:
        from luma.core.interface.serial import spi
        from luma.lcd.device import st7735
        from luma.core.render import canvas
        from PIL import ImageFont
    except ImportError as e:
        print(f"  [Дисплей] Не установлена библиотека: {e}")
        print("  [Дисплей] Запусти: pip install luma.lcd Pillow")
        return False

    print("  [Дисплей] Подключение к ST7735 через SPI...")
    try:
        serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24)
        # ST7735 1.8" = 160 x 128 (landscape), bgr=True для правильных цветов
        device = st7735(serial, width=160, height=128, bgr=True)
    except Exception as e:
        print(f"  [Дисплей] Ошибка инициализации: {e}")
        return False

    # Шаг 1: цветные полосы
    print("  [Дисплей] Рисуем цветные полосы (R, G, B, Y, W)...")
    try:
        colors = ["red", "green", "blue", "yellow", "white"]
        stripe_h = device.height // len(colors)
        with canvas(device) as draw:
            for i, color in enumerate(colors):
                y0 = i * stripe_h
                y1 = (i + 1) * stripe_h
                draw.rectangle([0, y0, device.width, y1], fill=color)
        time.sleep(2)
    except Exception as e:
        print(f"  [Дисплей] Ошибка при рисовании полос: {e}")
        return False

    # Шаг 2: текст
    print("  [Дисплей] Рисуем текст...")
    try:
        try:
            font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13
            )
        except OSError:
            font_large = ImageFont.load_default()
            font_small = font_large

        with canvas(device) as draw:
            draw.rectangle([0, 0, device.width, device.height], fill="black")
            draw.text((8, 15), "Smart Mirror", fill="white", font=font_large)
            draw.text((8, 45), "ST7735  OK", fill="#00ff00", font=font_small)
            draw.text((8, 65), "128 x 160 px", fill="#aaaaaa", font=font_small)
            draw.text((8, 90), "Test passed!", fill="cyan", font=font_small)
        time.sleep(3)
    except Exception as e:
        print(f"  [Дисплей] Ошибка при выводе текста: {e}")
        return False

    print("  [Дисплей] OK")
    return True


# ─── Тест: KY-012 зуммер ──────────────────────────────────────────────────────

def test_buzzer() -> bool:
    """
    KY-012 — активный зуммер (не пьезо-пищалка, не требует ШИМ).
    HIGH → пищит, LOW → тихо.
    Издаёт 3 коротких сигнала.
    """
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("  [Зуммер] Не установлена библиотека RPi.GPIO")
        print("  [Зуммер] Запусти: pip install RPi.GPIO")
        return False

    print("  [Зуммер] 3 сигнала...")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)
        for i in range(3):
            GPIO.output(PIN_BUZZER, GPIO.HIGH)
            time.sleep(BUZZER_BEEP_DURATION)
            GPIO.output(PIN_BUZZER, GPIO.LOW)
            time.sleep(BUZZER_PAUSE)
    except Exception as e:
        print(f"  [Зуммер] Ошибка: {e}")
        return False

    print("  [Зуммер] OK  (слышал 3 сигнала?)")
    return True


# ─── Тест: TTP223 кнопка ──────────────────────────────────────────────────────

def test_touch() -> bool:
    """
    TTP223 — ёмкостный сенсор.
    Когда пальцем касаешься площадки, вывод OUT становится HIGH.
    Ждём нажатие до TOUCH_WAIT_TIMEOUT секунд.
    """
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("  [Кнопка] Не установлена библиотека RPi.GPIO")
        return False

    print(f"  [Кнопка] Нажми на сенсор в течение {TOUCH_WAIT_TIMEOUT} сек...")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIN_TOUCH, GPIO.IN)

        deadline = time.monotonic() + TOUCH_WAIT_TIMEOUT
        while time.monotonic() < deadline:
            if GPIO.input(PIN_TOUCH) == GPIO.HIGH:
                print("  [Кнопка] Нажатие зафиксировано! OK")
                return True
            time.sleep(0.05)

    except Exception as e:
        print(f"  [Кнопка] Ошибка: {e}")
        return False

    print("  [Кнопка] TIMEOUT — нажатие не обнаружено за указанное время")
    return False


# ─── GPIO cleanup ─────────────────────────────────────────────────────────────

def _cleanup() -> None:
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
    except Exception:
        pass


# ─── Точка входа ─────────────────────────────────────────────────────────────

def main() -> int:
    print()
    print("=" * 52)
    print("  Smart Mirror — Тест железа")
    print("=" * 52)

    results: dict[str, bool] = {}

    # 1. Дисплей
    print("\n[1/3] ST7735 TFT дисплей")
    results["display"] = test_display()

    # 2. Зуммер
    print("\n[2/3] KY-012 зуммер")
    results["buzzer"] = test_buzzer()

    # 3. Кнопка
    print("\n[3/3] TTP223 сенсорная кнопка")
    results["touch"] = test_touch()

    _cleanup()

    # Итоговая таблица
    _icon = lambda ok: " OK  " if ok else "FAIL "
    print()
    print("=" * 52)
    print("  Результаты:")
    print(f"  [{_icon(results['display'])}] ST7735 дисплей")
    print(f"  [{_icon(results['buzzer'])}] KY-012 зуммер")
    print(f"  [{_icon(results['touch'])}]  TTP223 кнопка")
    print("=" * 52)

    all_ok = all(results.values())
    if all_ok:
        print("  Все компоненты работают!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  Не прошли тест: {', '.join(failed)}")
        print("  Проверь распиновку и соединения.")
    print()

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
