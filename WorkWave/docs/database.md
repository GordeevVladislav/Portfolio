# Схема базы данных

![Схема базы данных](../diagrams/db-schema.png)

Схема реализационной модели (Django). Служебные таблицы `auth_*` и `django_*` стандартны для фреймворка; предметные таблицы имеют префикс `core_`.

## Предметные таблицы

| Таблица | Назначение | Ключевые поля |
|---|---|---|
| `core_userprofile` | Профиль пользователя | `user_id`, `full_name`, `photo`, `phone`, `email`, `birth_date`, `bio` |
| `core_company` | Компания работодателя | `user_id`, `name`, `photo`, `phone`, `email`, `bio` |
| `core_vacancy` | Вакансия | `company_id`, `title`, `salary`, `photo`, `description`, `is_approved`, `created_at`, `updated_at` |
| `core_tag`, `core_vacancy_tags` | Теги вакансий (связь многие ко многим) | `vacancy_id`, `tag_id`, `name` |
| `core_application` | Отклик на вакансию | `user_id`, `vacancy_id`, `message`, `created_at` |
| `core_favoritevacancy` | Избранное | `user_id`, `vacancy_id`, `added_at` |
| `core_resume` | Резюме | `user_id`, `profession`, ФИО, `birth_date`, `gender`, `phone`, `citizenship`, `skills`, `created_at`, `updated_at` |
| `core_workexperience` | Опыт работы | `resume_id`, `company`, `position`, `responsibilities`, `achievements`, `date_start`, `date_end`, `currently_working` |
| `core_education` | Образование | `resume_id`, `institution`, `specialization`, `year_start`, `year_end` |
| `core_portfoliofile` | Файлы портфолио | `work_experience_id`, `file`, `description` |
| `core_chatmessage` | Сообщения чата | `sender_id`, `receiver_id`, `message`, `timestamp`, `is_read` |
| `core_emailverificationcode` | Коды подтверждения email | `email`, `code`, `purpose`, `created_at`, `is_used` |
| `core_skill` | Справочник навыков | `name` |

## Связи с требованиями

| Требование | Где отражено в схеме |
|---|---|
| Модерация вакансий (ФТ-7.3, ФТ-9.2) | `core_vacancy.is_approved` |
| Подтверждение email (ФТ-1.4) | `core_emailverificationcode` |
| Избранное (ФТ-4.4) | `core_favoritevacancy` |
| Чат (ФТ-5.10, ФТ-8.6) | `core_chatmessage` |
| Журнал действий администратора (ФТ-9.6) | `django_admin_log` |
