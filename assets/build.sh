#!/usr/bin/env bash
#
# Собирает PNG-ассеты из SVG-исходников по ТЗ.
# Требует rsvg-convert (brew install librsvg).
#
# Запуск:
#     ./assets/build.sh
#
# Идемпотентно: повторный запуск перезаписывает PNG из тех же SVG.
# Если что-то поправил в SVG — запусти заново.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT_DIR/source"
AVATAR_OUT="$ROOT_DIR/avatar"
BANNERS_OUT="$ROOT_DIR/banners"

if ! command -v rsvg-convert >/dev/null 2>&1; then
  echo "ERROR: rsvg-convert не найден. Установи: brew install librsvg" >&2
  exit 1
fi

mkdir -p "$AVATAR_OUT" "$BANNERS_OUT"

echo "==> Аватар 512×512"
rsvg-convert -w 512 -h 512 \
  "$SRC/bot-avatar-512.svg" \
  -o "$AVATAR_OUT/bot-avatar-512.png"

echo "==> Баннеры 1280×640"
for name in welcome trial contacts schedule; do
  rsvg-convert -w 1280 -h 640 \
    "$SRC/$name.svg" \
    -o "$BANNERS_OUT/$name-1280x640.png"
  echo "    - $name → $BANNERS_OUT/$name-1280x640.png"
done

echo ""
echo "==> Готово. Размеры файлов:"
ls -la "$AVATAR_OUT"/*.png "$BANNERS_OUT"/*.png 2>/dev/null | awk '{print "    " $5/1024 " КБ   " $9}'

echo ""
echo "Все ассеты должны быть ≤ 200 КБ — иначе Telegram режет качество."
echo "Аватар загружается в @BotFather через /setuserpic."
echo "Баннеры — через bot.send_photo(InputFile(...)) в нужных хендлерах."
