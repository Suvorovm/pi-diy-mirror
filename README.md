# Smart Mirror

Приложение умного зеркала для **Raspberry Pi Zero 2W**.  
Отображает время, погоду и фразы дня. Управляется с телефона по MQTT.

---

## Содержание

1. [Требования](#требования)
2. [Установка на Raspberry Pi](#установка-на-raspberry-pi)
3. [Первый запуск](#первый-запуск)
4. [Автозапуск при старте системы](#автозапуск-при-старте-системы)
5. [Тест железа](#тест-железа)
6. [Структура файлов](#структура-файлов)
7. [MQTT API](#mqtt-api)

---

## Требования

| Компонент         | Версия / описание                     |
|-------------------|---------------------------------------|
| Raspberry Pi OS   | Bookworm (64-bit) или Bullseye        |
| Python            | 3.11 или новее (`python3 --version`)  |
| MQTT-брокер       | Mosquitto на самом Pi или в сети      |
| Интернет          | Нужен для погоды и авто-локации       |

---

## Установка на Raspberry Pi

### 1. Клонируй репозиторий

```bash
git clone <url-репозитория> ~/smart-mirror
cd ~/smart-mirror
```

### 2. Создай venv и установи зависимости

GPIO на Raspberry Pi требует `sudo`, а `sudo` не видит глобально установленные пакеты.
Поэтому используем venv и запускаем скрипты через `run.sh`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Сделай `run.sh` исполняемым

```bash
chmod +x run.sh
```

`run.sh` автоматически передаёт `sudo` правильный Python из venv:
```bash
./run.sh main.py            # основное приложение
./run.sh test_hardware.py   # тест железа
```

> **Почему нельзя просто `sudo python3`?**  
> `sudo` сбрасывает переменные окружения и использует системный Python,
> который не видит пакеты из venv. `run.sh` решает это, передавая полный путь
> к `.venv/bin/python3` напрямую в `sudo`.

### 4. Установи и запусти MQTT-брокер (Mosquitto)

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

По умолчанию брокер слушает порт `1883` на `localhost`.  
Если брокер стоит на другом устройстве — поменяй `broker_host` в `config.json`.

### 5. Разреши перезагрузку без пароля (для команды `device/restart`)

```bash
echo "pi ALL=(ALL) NOPASSWD: /sbin/reboot" | sudo tee /etc/sudoers.d/smartmirror
```

### 6. Настрой `config.json` под свои нужды

```json
{
  "mqtt": {
    "broker_host": "localhost",
    "broker_port": 1883,
    "topic_prefix": "mirror/"
  },
  "weather": {
    "latitude": 55.75,
    "longitude": 37.62,
    "refresh_interval_seconds": 300
  },
  "intervals": {
    "time_seconds": 60,
    "phrase_seconds": 1800,
    "alarm_check_seconds": 60
  },
  "phrases_file": "smart_mirror/data/phrases.json",
  "display_type": "st7735"
}
```

| Поле           | Значения             | Описание                                              |
|----------------|----------------------|-------------------------------------------------------|
| `display_type` | `"console"` / `"st7735"` | Тип дисплея. `console` — вывод в терминал (для разработки), `st7735` — TFT-экран + GPIO-железо на Pi |

> Координаты по умолчанию используются только если локация не определена автоматически по IP и не задана командой `location/set`.

---

## Первый запуск

```bash
cd ~/smart-mirror
./run.sh main.py
```

При запуске приложение:
1. Читает `config.json` (в т.ч. `display_type` — выбирает дисплей и GPIO-железо)
2. Пытается определить местоположение по IP (ip-api.com) — если не задано вручную
3. Запускает рутины: время, погода, фразы, проверка будильника
4. Подключается к MQTT-брокеру и ждёт команд

**Поведение будильника:**  
Когда время совпадает с установленным — включается зуммер KY-012 и на экране появляется баннер.  
Зуммер отключается только после прикосновения к кнопке TTP223.  
При `display_type: "console"` вместо зуммера — сообщение в логе, вместо кнопки — нажатие Enter.

**Пример вывода в консоль:**

```
----------------------------------------
  Время:    09:15
  Место:    Москва (55.7500, 37.6200)
----------------------------------------
  Погода:   Ясно
  Темп:     18.3°C
  Ветер:    7.0 км/ч
----------------------------------------
  >> Сделай сегодня то, за что завтра скажешь себе спасибо.
----------------------------------------
  Будильник: 07:30
----------------------------------------
```

Остановить: `Ctrl+C`.

---

## Автозапуск при старте системы

Чтобы приложение запускалось само при включении Pi:

```bash
# Создаём systemd-сервис
sudo nano /etc/systemd/system/smart_mirror.service
```

Содержимое файла:

```ini
[Unit]
Description=Smart Mirror
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/smart-mirror
ExecStart=/home/pi/smart-mirror/.venv/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> Используем `User=root` и прямой путь к `.venv/bin/python3` — так systemd
> запускает приложение с правами GPIO и видит все пакеты из venv.

Включить и запустить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable smart_mirror
sudo systemctl start smart_mirror

# Смотреть логи в реальном времени:
sudo journalctl -u smart_mirror -f
```

---

## Тест железа

Перед первым запуском основного приложения убедись, что все компоненты подключены правильно.

**Компоненты:** ST7735 TFT 1.8" 160×128 (SPI0), TTP223 (кнопка), KY-012 (зуммер).

### Распиновка

**ST7735 (SPI0)**

| ST7735 | GPIO     | Pi Pin |
|--------|----------|--------|
| VCC    | 3.3V     | Pin 1  |
| GND    | GND      | Pin 6  |
| SCL    | GPIO11 (SCLK) | Pin 23 |
| SDA    | GPIO10 (MOSI) | Pin 19 |
| RES    | GPIO24   | Pin 18 |
| DC     | GPIO25   | Pin 22 |
| CS     | GPIO8 (CE0) | Pin 24 |
| BL/LED | 3.3V     | Pin 1 или 17 |

**TTP223 (сенсорная кнопка)**

| TTP223 | GPIO   |
|--------|--------|
| VCC    | 3.3V   |
| GND    | GND    |
| OUT    | GPIO17 |

**KY-012 (активный зуммер)**

| KY-012 | GPIO   |
|--------|--------|
| S      | GPIO19 |
| +      | 3.3V   |
| -      | GND    |

### Установка зависимостей для теста

Все зависимости уже в общем `requirements.txt` — дополнительно ничего ставить не нужно.

Включи SPI, если ещё не включено:

```bash
sudo raspi-config
# → Interface Options → SPI → Enable → Finish
sudo reboot
```

### Запуск теста

```bash
./run.sh test_hardware.py
```

> `sudo python3 test_hardware.py` — **не работает**: sudo видит системный Python,
> а не пакеты из venv. `run.sh` решает это автоматически.

Скрипт по очереди проверит каждый компонент и выведет итог:

```
====================================================
  Результаты:
  [ OK  ] ST7735 дисплей
  [ OK  ] KY-012 зуммер
  [ OK  ]  TTP223 кнопка
====================================================
  Все компоненты работают!
```

---

## Структура файлов

```
smart-mirror/
├── main.py                        ← точка входа
├── run.sh                         ← запускает скрипты через venv + sudo
├── config.json                    ← настройки (MQTT, погода, интервалы, display_type)
├── settings.json                  ← данные пользователя (будильник, локация)
├── requirements.txt               ← все зависимости проекта
├── test_hardware.py               ← тест железа (не часть приложения)
└── smart_mirror/
    ├── core/
    │   ├── config.py              ← Config (читает config.json)
    │   ├── settings.py            ← SettingsManager (будильник, локация)
    │   └── app.py                 ← SmartMirrorApp (start/stop/run_forever)
    ├── commands/
    │   ├── command.py             ← Command ABC + CommandPayload
    │   ├── registry.py            ← CommandRegistry (topic → Command)
    │   ├── set_alarm.py
    │   ├── clear_alarm.py
    │   ├── set_location.py
    │   └── restart_device.py
    ├── routines/
    │   ├── routine.py             ← Routine ABC
    │   ├── runner.py              ← RoutineRunner (daemon thread на рутину)
    │   ├── time_routine.py
    │   ├── weather_routine.py
    │   ├── phrase_routine.py
    │   └── alarm_check_routine.py
    ├── display/
    │   ├── display_adapter.py     ← DisplayAdapter ABC
    │   ├── screen_state.py        ← ScreenState dataclass
    │   ├── console_display.py     ← вывод в терминал
    │   └── st7735_display.py      ← ST7735 TFT через luma.lcd
    ├── hardware/
    │   ├── buzzer/
    │   │   ├── buzzer_adapter.py  ← BuzzerAdapter ABC
    │   │   ├── console.py         ← ConsoleBuzzer (лог)
    │   │   └── ky012.py           ← Ky012Buzzer (GPIO19)
    │   └── button/
    │       ├── touch_button_adapter.py ← TouchButtonAdapter ABC
    │       ├── console.py         ← ConsoleButton (Enter)
    │       └── ttp223.py          ← Ttp223Button (GPIO17, RISING edge)
    ├── alarm/
    │   └── handler.py             ← AlarmHandler (дисплей + зуммер + кнопка)
    ├── mqtt/
    │   └── client.py              ← MqttClient (paho wrapper)
    ├── weather/
    │   └── fetcher.py             ← WeatherFetcher (Open-Meteo, без ключа)
    ├── location/
    │   └── detector.py            ← LocationDetector (ip-api.com, без ключа)
    └── data/
        ├── alarm.py
        ├── weather.py
        ├── location.py
        └── phrases.json
```

`settings.json` создаётся и перезаписывается автоматически — не редактируй вручную.

---

## MQTT API

## Подключение к брокеру

Параметры задаются в `config.json` → секция `mqtt`.

| Параметр      | Значение по умолчанию |
|---------------|----------------------|
| `broker_host` | `localhost`          |
| `broker_port` | `1883`               |
| `topic_prefix`| `mirror/`            |

> Если MQTT-брокер стоит на самом Pi — указывай его IP-адрес в мобильном приложении.  
> Пример: `192.168.1.42`, порт `1883`.

---

## Формат сообщений

Все сообщения отправляются **мобильным приложением → Pi**.

```
Топик:   mirror/<команда>
Payload: JSON (UTF-8)
QoS:     0 или 1
Retain:  не нужен
```

---

## Команды

| # | Топик               | Описание                         |
|---|---------------------|----------------------------------|
| 1 | `alarm/set`         | Установить будильник             |
| 2 | `alarm/clear`       | Удалить будильник                |
| 3 | `location/set`      | Изменить местоположение          |
| 4 | `device/restart`    | Перезагрузить устройство         |

---

### 1. Установить будильник — `alarm/set`

**Топик:** `mirror/alarm/set`

**Payload:**
```json
{
  "hour": 7,
  "minute": 30
}
```

| Поле     | Тип   | Допустимые значения |
|----------|-------|---------------------|
| `hour`   | `int` | 0 – 23              |
| `minute` | `int` | 0 – 59              |

**Что происходит:**
- Будильник сохраняется в `settings.json`
- На экране появляется время будильника
- Каждые `alarm_check_seconds` (60 сек) `AlarmCheckRoutine` сверяет время
- При совпадении: включается зуммер KY-012 + на экране появляется баннер
- Зуммер отключается только после прикосновения к кнопке TTP223

**Примеры:**
```json
{"hour": 6, "minute": 0}    // 06:00
{"hour": 7, "minute": 30}   // 07:30
{"hour": 22, "minute": 45}  // 22:45
```

---

### 2. Удалить будильник — `alarm/clear`

**Топик:** `mirror/alarm/clear`

**Payload:** пустой объект
```json
{}
```

**Что происходит:**
- Будильник удаляется из `settings.json`
- На экране пропадает строка с будильником
- `AlarmCheckRoutine` перестаёт проверять время до следующего `alarm/set`

---

### 3. Изменить местоположение — `location/set`

**Топик:** `mirror/location/set`

**Payload:**
```json
{
  "latitude": 59.93,
  "longitude": 30.32,
  "city": "Санкт-Петербург"
}
```

| Поле        | Тип      | Допустимые значения | Обязателен |
|-------------|----------|---------------------|-----------|
| `latitude`  | `float`  | -90 – 90            | Да        |
| `longitude` | `float`  | -180 – 180          | Да        |
| `city`      | `string` | любое название      | Нет       |

**Что происходит:**
- Координаты сохраняются в `settings.json`
- На экране обновляется строка с местоположением
- Следующий тик `WeatherRoutine` запросит погоду для новых координат

> **Приоритет источников локации:**  
> Сохранённые координаты (`settings.json`) > авто-определение по IP > дефолт из `config.json`

**Примеры:**
```json
{"latitude": 55.75, "longitude": 37.62, "city": "Москва"}
{"latitude": 59.93, "longitude": 30.32, "city": "Санкт-Петербург"}
{"latitude": 48.85, "longitude": 2.35,  "city": "Париж"}
```

---

### 4. Перезагрузить устройство — `device/restart`

**Топик:** `mirror/device/restart`

**Payload:** пустой объект
```json
{}
```

**Что происходит:**
- Pi выполняет `sudo reboot`

> ⚠️ **Требуется настройка sudoers на Pi:**
> ```bash
> echo "pi ALL=(ALL) NOPASSWD: /sbin/reboot" | sudo tee /etc/sudoers.d/smartmirror
> ```

---

## Что приложение показывает само (без команд)

Эти данные обновляются автоматически по расписанию — команд отправлять не нужно.

| Данные            | Интервал обновления                          | Источник                     |
|-------------------|----------------------------------------------|------------------------------|
| Текущее время     | `intervals.time_seconds` (60 с)              | Системные часы Pi            |
| Местоположение    | Определяется **один раз при старте** по IP   | ip-api.com                   |
| Погода            | `weather.refresh_interval_seconds` (300 с)   | Open-Meteo API               |
| Фраза             | `intervals.phrase_seconds` (1800 с)          | `data/phrases.json`          |
| Проверка будильника | `intervals.alarm_check_seconds` (60 с)     | `settings.json`              |
| Зуммер (будильник) | Включается при срабатывании, выключается по кнопке | KY-012 GPIO19 / лог |

---

## Настройка `config.json`

Все параметры меняются в `config.json` — перезапуск приложения обязателен.

### Тип дисплея

```json
{ "display_type": "st7735" }
```

| Значение    | Что включается                                              |
|-------------|-------------------------------------------------------------|
| `"console"` | Вывод в терминал, зуммер → лог, кнопка → Enter в stdin     |
| `"st7735"`  | TFT-экран (SPI), зуммер KY-012 (GPIO19), кнопка TTP223 (GPIO17) |

### Интервалы обновления

```json
{
  "intervals": {
    "time_seconds": 60,
    "phrase_seconds": 1800,
    "alarm_check_seconds": 60
  },
  "weather": {
    "refresh_interval_seconds": 300
  }
}
```

---

## Настройка координат по умолчанию

Используются только если локация не была определена по IP и не задана командой `location/set`.

```json
{
  "weather": {
    "latitude": 55.75,
    "longitude": 37.62
  }
}
```

Координаты можно найти на [latlong.net](https://www.latlong.net/).

---

## Как добавить новую команду (для разработчика)

1. Создать файл `smart_mirror/commands/your_command.py`:

```python
from dataclasses import dataclass
from smart_mirror.commands.command import Command, CommandPayload

@dataclass
class YourPayload(CommandPayload):
    some_field: str

class YourCommand(Command):
    @staticmethod
    def topic() -> str:
        return "your/topic"   # ← sub-topic после префикса

    @staticmethod
    def parse_payload(raw: dict) -> YourPayload:
        return YourPayload(some_field=raw["some_field"])

    def execute(self, payload: YourPayload) -> None:
        # делай что нужно
        self._display.update_phrase(payload.some_field)
```

2. Зарегистрировать в `main.py`:

```python
registry.register(YourCommand)
```

Полный топик будет: `mirror/your/topic`

---

## Примеры для каждой команды

Во всех примерах замени `<IP_Pi>` на реальный IP-адрес Raspberry Pi в твоей сети (например `192.168.1.42`).

---

### alarm/set — установить будильник

**mosquitto (терминал):**
```bash
mosquitto_pub -h <IP_Pi> -p 1883 -t "mirror/alarm/set" -m '{"hour": 7, "minute": 30}'
```

**Python (paho-mqtt):**
```python
import paho.mqtt.publish as publish
import json

publish.single(
    topic="mirror/alarm/set",
    payload=json.dumps({"hour": 7, "minute": 30}),
    hostname="<IP_Pi>",
    port=1883,
)
```

**Dart / Flutter (mqtt_client):**
```dart
final payload = jsonEncode({'hour': 7, 'minute': 30});
final builder = MqttClientPayloadBuilder()..addString(payload);
client.publishMessage('mirror/alarm/set', MqttQos.atLeastOnce, builder.payload!);
```

---

### alarm/clear — удалить будильник

**mosquitto (терминал):**
```bash
mosquitto_pub -h <IP_Pi> -p 1883 -t "mirror/alarm/clear" -m '{}'
```

**Python (paho-mqtt):**
```python
import paho.mqtt.publish as publish

publish.single(
    topic="mirror/alarm/clear",
    payload="{}",
    hostname="<IP_Pi>",
    port=1883,
)
```

**Dart / Flutter (mqtt_client):**
```dart
final builder = MqttClientPayloadBuilder()..addString('{}');
client.publishMessage('mirror/alarm/clear', MqttQos.atLeastOnce, builder.payload!);
```

---

### location/set — изменить местоположение

**mosquitto (терминал):**
```bash
mosquitto_pub -h <IP_Pi> -p 1883 -t "mirror/location/set" \
  -m '{"latitude": 59.93, "longitude": 30.32, "city": "Санкт-Петербург"}'
```

**Python (paho-mqtt):**
```python
import paho.mqtt.publish as publish
import json

publish.single(
    topic="mirror/location/set",
    payload=json.dumps({"latitude": 59.93, "longitude": 30.32, "city": "Санкт-Петербург"}),
    hostname="<IP_Pi>",
    port=1883,
)
```

**Dart / Flutter (mqtt_client):**
```dart
final payload = jsonEncode({
  'latitude': 59.93,
  'longitude': 30.32,
  'city': 'Санкт-Петербург',
});
final builder = MqttClientPayloadBuilder()..addString(payload);
client.publishMessage('mirror/location/set', MqttQos.atLeastOnce, builder.payload!);
```

---

### device/restart — перезагрузить Pi

**mosquitto (терминал):**
```bash
mosquitto_pub -h <IP_Pi> -p 1883 -t "mirror/device/restart" -m '{}'
```

**Python (paho-mqtt):**
```python
import paho.mqtt.publish as publish

publish.single(
    topic="mirror/device/restart",
    payload="{}",
    hostname="<IP_Pi>",
    port=1883,
)
```

**Dart / Flutter (mqtt_client):**
```dart
final builder = MqttClientPayloadBuilder()..addString('{}');
client.publishMessage('mirror/device/restart', MqttQos.atLeastOnce, builder.payload!);
```

> ⚠️ **Важно:** перед использованием настрой sudoers на Pi:
> ```bash
> echo "pi ALL=(ALL) NOPASSWD: /sbin/reboot" | sudo tee /etc/sudoers.d/smartmirror
> ```

---

### Полный тест всех команд подряд (bash-скрипт)

```bash
#!/bin/bash
PI_IP="192.168.1.42"

echo "Устанавливаем будильник на 7:30..."
mosquitto_pub -h $PI_IP -t "mirror/alarm/set" -m '{"hour": 7, "minute": 30}'
sleep 1

echo "Меняем местоположение на СПб..."
mosquitto_pub -h $PI_IP -t "mirror/location/set" \
  -m '{"latitude": 59.93, "longitude": 30.32, "city": "Санкт-Петербург"}'
sleep 1

echo "Удаляем будильник..."
mosquitto_pub -h $PI_IP -t "mirror/alarm/clear" -m '{}'
sleep 1

echo "Перезагружаем Pi..."
mosquitto_pub -h $PI_IP -t "mirror/device/restart" -m '{}'
```
