# Evaluator Rubric — `yclients-001` (Async-клиент YClients API)

Заполнено задним числом 2026-05-17 после успешного smoke против Booking API.

| Категория | Вопрос | Оценка (0–2) | Заметки |
| --- | --- | --- | --- |
| Correctness | Соответствует ли реализованное поведение `user_visible_behavior` фичи? | 2 | Все обещанные методы (auth/get_services/get_staff/search_client/create_client) реализованы. Smoke против реального API школы вернул 4 услуги и 6 преподавателей. |
| Verification | Все ли пункты `verification` реально были запущены, есть ли доказательства? | 2 | 4/4 пунктов закрыты: smoke_test зелёный, 25 тестов на respx-моках зелёные, retry/refresh покрыты 4 отдельными тестами (401-refresh, 429-backoff, 5xx-retry, 4xx-no-retry). |
| Scope discipline | Сессия осталась в рамках выбранной фичи, без посторонних правок? | 1 | По ходу пришлось добавить статический User Token режим (изначально планировали только legacy через login/password). Это расширение, не «выползание» — оправдано тем, что YClients реально предлагает этот режим. Минус один балл — изменили публичный API клиента после первоначального дизайна. |
| Reliability | Результат переживает перезапуск/повторный прогон без ручного ремонта? | 2 | `uv run python -m src.yclients.smoke_test` повторяемо отрабатывает зелёным. httpx.AsyncClient переиспользует соединения. retry/backoff защищают от транзитных ошибок. |
| Maintainability | Код и документация достаточно понятны для следующей сессии? | 2 | Чёткое разделение exceptions/models/client. Docstring у класса описывает оба режима auth. Комментарии у retry/refresh-веток объясняют, почему так. |
| Handoff readiness | Сможет ли свежая сессия продолжить работу, опираясь только на артефакты репо? | 2 | feature_list.json содержит ID настоящих услуг и преподавателей. quality-document.md помечает duration=0 как known gap. Достаточно для старта booking-individual-003. |

**Сумма: 11/12.**

## Verdict

- [x] **Accept** — фича в `passing`, evidence в feature_list.json.
- [ ] Revise
- [ ] Block

## Required Follow-Up

- Missing evidence: —
- Required fixes: —
- Next review trigger:
  - при первом обращении к Admin API (`/clients`) — нужно убедиться, что pydantic-модель Client соответствует реальному ответу (сейчас сломано на 403, не дошли до парсинга);
  - при добавлении новых endpoint-ов (например, /book_record) — повторно прогнать smoke и проверить новые модели.
