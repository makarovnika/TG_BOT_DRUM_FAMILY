# assets/

Визуальные ассеты бота: аватар + 4 баннера.

## Структура

```
assets/
├── source/                 ← SVG-исходники (правь только их)
│   ├── bot-avatar-512.svg
│   ├── welcome.svg
│   ├── trial.svg
│   ├── contacts.svg
│   └── schedule.svg
├── avatar/                 ← PNG-результат для @BotFather
│   └── bot-avatar-512.png  (генерируется)
├── banners/                ← PNG-результат для send_photo
│   ├── welcome-1280x640.png   (генерируется)
│   ├── trial-1280x640.png     (генерируется)
│   ├── contacts-1280x640.png  (генерируется)
│   └── schedule-1280x640.png  (генерируется)
└── build.sh                ← собирает PNG из всех SVG
```

## Как собрать PNG

```sh
# 1. Один раз поставь rsvg-convert
brew install librsvg

# 2. Собери ассеты
./assets/build.sh
```

После этого PNG появятся в `avatar/` и `banners/`. Скрипт идемпотентный —
повторный запуск перезаписывает из текущих SVG.

## Что делать с готовыми ассетами

- **Аватар** → загрузить в @BotFather: команда `/setuserpic`, выбрать
  чат с ботом, отправить файл `bot-avatar-512.png`.
- **Баннеры** → подцепляются в коде через `bot.send_photo(InputFile(...))`
  в нужных хендлерах (см. `botfather/botfather-setup.md` §3).

## Цвета и шрифты (берутся из ТЗ §3 и §4)

| Назначение | HEX |
|---|---|
| Главный голубой | `#0A91C4` |
| Голубой светлый | `#12B1EB` |
| Голубой тёмный | `#0076B8` |
| Акцент красный | `#EB3800` |
| Оранжевый | `#F69400` |
| Чёрный | `#000000` |
| Белый | `#FFFFFF` |

Шрифт всех заголовков — **Onest** (Black/Bold), у Google Fonts:
https://fonts.google.com/specimen/Onest

В SVG прописан `font-family="Onest, system-ui, sans-serif"` — если
Onest не установлен в системе сборки (rsvg-convert), будет использован
system-ui. Чтобы было точно как в ТЗ:

```sh
# на Mac
mkdir -p ~/Library/Fonts/Onest
curl -L https://fonts.google.com/download?family=Onest -o /tmp/onest.zip
unzip /tmp/onest.zip -d ~/Library/Fonts/Onest
```

## Замечание про DF-логотип

В `bot-avatar-512.svg` сейчас — стилизованный «барабан + буквы DF»,
собранный вручную из примитивов. Если у школы есть оригинальный
векторный логотип DF из брендбука — замени группу `<g id="df-mark">`
на импорт оригинала. Главное — сохранить квадратный bbox в центре
`(256, 256)` со стороной ≥ 256 px.

Та же замена применима к баннерам, где DF-марка в правом верхнем углу
(88×88 квадратик).
