# Smart Mirror — MQTT API

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

### 1. Установить будильник

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
- В `alarm_check_seconds` секунд (по умолчанию 60) `AlarmCheckRoutine` сверит время — если совпадёт, покажет уведомление

**Пример — будильник на 7:30:**
```json
{"hour": 7, "minute": 30}
```

---

### 2. Перезагрузить устройство

**Топик:** `mirror/device/restart`

**Payload:** пустой JSON-объект (или вообще пустая строка)
```json
{}
```

**Что происходит:**
- Pi выполняет `sudo reboot`
- Требуется настройка sudoers (см. ниже)

> ⚠️ **Для работы перезагрузки** нужно добавить на Pi:
> ```bash
> echo "pi ALL=(ALL) NOPASSWD: /sbin/reboot" | sudo tee /etc/sudoers.d/smartmirror
> ```

---

## Что приложение показывает само (без команд)

Эти данные обновляются автоматически по расписанию — команд отправлять не нужно.

| Данные       | Интервал обновления              | Источник                  |
|--------------|----------------------------------|---------------------------|
| Текущее время| `intervals.time_seconds` (60 с)  | Системные часы Pi         |
| Погода       | `weather.refresh_interval_seconds` (300 с) | Open-Meteo API  |
| Фраза        | `intervals.phrase_seconds` (1800 с) | `data/phrases.json`   |
| Будильник    | Проверка каждые `alarm_check_seconds` (60 с) | `settings.json` |

---

## Настройка интервалов

Все интервалы меняются в `config.json` — перезапуск приложения обязателен.

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

## Настройка координат для погоды

```json
{
  "weather": {
    "latitude": 55.75,
    "longitude": 37.62
  }
}
```

Широта и долгота города. Сейчас стоит Москва.  
Координаты можно найти на [latlong.net](https://www.latlong.net/).

---

## Как добавить новую команду (для разработчика)

1. Создать файл `smart_mirror/commands/your_command.py`:

```python
from dataclasses import dataclass
from smart_mirror.commands.base import Command, CommandPayload

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

**JavaScript / Node.js (mqtt):**
```js
const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://<IP_Pi>:1883');

client.on('connect', () => {
    client.publish(
        'mirror/alarm/set',
        JSON.stringify({ hour: 7, minute: 30}),
        () => client.end()
    );
});
```

**Dart / Flutter (mqtt_client):**
```dart
final payload = jsonEncode({'hour': 7, 'minute': 30});
final builder = MqttClientPayloadBuilder()..addString(payload);
client.publishMessage('mirror/alarm/set', MqttQos.atLeastOnce, builder.payload!);
```

**Варианты будильника:**
```json
{"hour": 6, "minute": 0}    // 06:00
{"hour": 7, "minute": 30}   // 07:30
{"hour": 22, "minute": 45}  // 22:45
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

**JavaScript / Node.js (mqtt):**
```js
const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://<IP_Pi>:1883');

client.on('connect', () => {
    client.publish('mirror/device/restart', '{}', () => client.end());
});
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

echo "Меняем будильник на 8:00..."
mosquitto_pub -h $PI_IP -t "mirror/alarm/set" -m '{"hour": 8, "minute": 0}'
sleep 1

echo "Перезагружаем Pi..."
mosquitto_pub -h $PI_IP -t "mirror/device/restart" -m '{}'
```
