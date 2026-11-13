#!/usr/bin/env python3
"""Расчетная модель стратегии роста продуктового проникновения ВТБ (СМБ, торговля, Москва и МО).

Источники данных кейса: база 300 тыс. клиентов, 20% «спящих», доля торговли 28,9%,
300 клиентов на менеджера, 35-40 тыс. ₽/год расходов на услуги, поток регистраций
(Московская область, 2024: 14,5 тыс. организаций и 73 тыс. ИП; Москва: организаций
в 3,15 раза больше, чем в области, по численности юрлиц).
Все, что помечено ASSUMPTION, это допущения команды, а не данные кейса.

Запуск: python3 calc/model.py  (читает calc/assumptions.json, пишет calc/RESULTS.generated.md и calc/key_figures.json)
"""
import json
from pathlib import Path

# ---------- Входные данные: calc/assumptions.json ----------
CFG = json.loads((Path(__file__).with_name("assumptions.json")).read_text(encoding="utf-8"))
CD, AS = CFG["case_data"], CFG["assumptions"]

BASE = CD["base"]
TRADE_SHARE = CD["trade_share"]
SLEEPING_SHARE = CD["sleeping_share"]
CLIENTS_PER_MANAGER = CD["clients_per_manager"]
RUSSIA_TRADE = CD["russia_trade"]
REG_MO_ORG, REG_MO_IP = CD["reg_mo_org"], CD["reg_mo_ip"]
LEGAL_ENTITIES_MSK, LEGAL_ENTITIES_MO = CD["legal_entities_msk"], CD["legal_entities_mo"]

RAMP_MONTHS_EXISTING = AS["ramp_months_existing"]
RAMP_MONTHS_NEW = AS["ramp_months_new"]
WAVES = [tuple(w) for w in AS["waves"]]
COVERAGE = sum(share for _, share in WAVES)
START_AVG = None                # считается из корзины

BASKET = {k: tuple(v) for k, v in AS["basket"].items()}     # продукт -> (тип, сейчас, цель)
PAID = {k: tuple(v) for k, v in AS["paid"].items()}         # продукт -> (доля платящих, платеж ₽/год)
ACQ_HIGH = AS["acquiring_high"]["turnover"] * AS["acquiring_high"]["commission"]
ACQ_LOW = AS["acquiring_low"]["turnover"] * AS["acquiring_low"]["commission"]
NEW_BASKET = AS["new_basket"]
NEW_CLIENTS_PER_YEAR_SHARE = AS["new_share_scenarios"]
NEW_START = AS["new_start"]
NEW_TARGET = AS["new_target"]
MANAGER_HANDLED = AS["manager_handled"]
HOURS_PER_CONNECTION = AS["hours_per_connection"]
HOURS_PER_MONTH = AS["hours_per_month"]

out = []


def p(line=""):
    out.append(line)
    print(line)


def table(headers, rows):
    p("| " + " | ".join(headers) + " |")
    p("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        p("| " + " | ".join(str(x) for x in r) + " |")
    p()


def n0(x):
    return f"{x:,.0f}".replace(",", " ")


def f1(x):
    return f"{x:,.1f}".replace(",", " ").replace(".", ",")


def f2(x):
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


# ---------- 1. Размер сегмента ----------
trade = BASE * TRADE_SHARE
sleeping = trade * SLEEPING_SHARE
active = trade - sleeping
p("<!-- Файл создан calc/model.py, вручную не править. Входные данные: calc/assumptions.json -->")
p("# Результаты расчета")
p()
p("## 1. Размер сегмента (торговля, Москва и МО)")
table(["Показатель", "Значение"], [
    ["Клиентов в торговле", f"{trade:,.0f}".replace(",", " ")],
    ["«Спящих» (20%)", f"{sleeping:,.0f}".replace(",", " ")],
    ["Активных", f"{active:,.0f}".replace(",", " ")],
    ["Менеджеров, эквивалент (клиентов / 300)", f"{trade / CLIENTS_PER_MANAGER:,.0f}"],
])

# ---------- 2. Корзина действующих ----------
now_bank = sum(v[1] for v in BASKET.values() if v[0] == "банк")
now_non = sum(v[1] for v in BASKET.values() if v[0] == "небанк")
tgt_bank = sum(v[2] for v in BASKET.values() if v[0] == "банк")
tgt_non = sum(v[2] for v in BASKET.values() if v[0] == "небанк")
now_total, tgt_total = now_bank + now_non, tgt_bank + tgt_non
delta = tgt_total - now_total
START_AVG = now_total
p("## 2. Корзина действующих клиентов (на одного охваченного)")
rows = [[k, v[0], f2(v[1]), f2(v[2]), "+" + f2(v[2] - v[1])] for k, v in BASKET.items()]
rows.append(["Итого банковские", "", f2(now_bank), f2(tgt_bank), "+" + f2(tgt_bank - now_bank)])
rows.append(["Итого небанковские", "", f2(now_non), f2(tgt_non), "+" + f2(tgt_non - now_non)])
rows.append(["Всего", "", f2(now_total), f2(tgt_total), "+" + f2(delta)])
table(["Продукт", "Тип", "Сейчас", "Цель", "Прирост"], rows)

nb_alt_total = tgt_bank + 1.0
p(f"Сценарий «небанковские = 1,0»: итог {f2(nb_alt_total)} (цель 5 не закрывается).")
p(f"Только банковские продукты: максимум {f2(tgt_bank)}.")
p()

# ---------- 3. Траектория ----------
def progress(month, start):
    return min(1.0, max(0.0, (month - start) / RAMP_MONTHS_EXISTING))


def avg_covered(month):
    num = den = 0.0
    for start, share in WAVES:
        if month >= start:
            num += share * (START_AVG + delta * progress(month, start))
            den += share
    return (num / den, den) if den else (START_AVG, 0.0)


p("## 3. Траектория проникновения (действующие, торговля)")
rows = []
for m in (3, 6, 9, 12, 15, 18):
    a, cov = avg_covered(m)
    covered = active * cov
    seg = START_AVG + (a - START_AVG) * cov
    rows.append([m, f"{cov:.0%}", f1(covered / 1000), f2(a), f2(seg)])
table(["Месяц", "Охват активных", "Охвачено, тыс.", "Среднее у охваченных", "Среднее по активным торговли"], rows)

# альтернатива: выход когорты за 9 месяцев
def avg_alt(month, ramp):
    num = den = 0.0
    for start, share in WAVES:
        if month >= start:
            pr = min(1.0, max(0.0, (month - start) / ramp))
            num += share * (START_AVG + delta * pr)
            den += share
    return num / den

p(f"Консервативный сценарий (выход на цель за 9 месяцев): среднее у охваченных на 18-м месяце "
  f"{f2(avg_alt(18, 9))}; цель достигается на 21-м месяце (последняя волна стартует на 12-м).")
p()

covered_final = active * COVERAGE
extra_products = covered_final * delta
p("## 4. Вклад в цель ВТБ")
table(["Показатель", "Значение"], [
    ["Охвачено клиентов (40% активных)", f"{covered_final:,.0f}".replace(",", " ")],
    ["Дополнительных используемых продуктов", f"{extra_products:,.0f}".replace(",", " ")],
    ["Прирост среднего по базе Москвы и МО (300 тыс.)", "+" + f2(extra_products / BASE)],
    ["Среднее по базе: было -> стало", f"{f2(START_AVG)} -> {f2(START_AVG + extra_products / BASE)}"],
])

# ---------- 5. Экономика действующих ----------
def economics(users_factor=1.0, coverage=COVERAGE, nonbank_scale=1.0, acq=ACQ_HIGH):
    cov_clients = active * coverage * users_factor
    res = {}
    for prod, (typ, a, b) in BASKET.items():
        if prod not in PAID:
            continue
        users = cov_clients * (b - a) * (nonbank_scale if typ == "небанк" else 1.0)
        share, price = PAID[prod]
        res[prod] = (typ, users, users * share, users * share * price)
    acq_users = cov_clients * (BASKET["Эквайринг"][2] - BASKET["Эквайринг"][1])
    return res, acq_users * acq


res, acq_high = economics()
_, acq_low = economics(acq=ACQ_LOW)
nonbank_rev = sum(v[3] for v in res.values() if v[0] == "небанк")
bank_core = sum(v[3] for v in res.values() if v[0] == "банк")
core = nonbank_rev + bank_core
p()
p("## 5. Экономика: действующие клиенты, охват 40% (млн ₽/год)")
rows = [[k, v[0], f1(v[1] / 1000), f1(v[2] / 1000), f"{PAID[k][1]:,}".replace(",", " "), f1(v[3] / 1e6)]
        for k, v in res.items()]
table(["Продукт", "Тип", "Пользователей, тыс.", "Платящих, тыс.", "Платеж, ₽/год", "Выручка, млн ₽"], rows)
table(["Блок", "Млн ₽/год"], [
    ["Небанковские", f1(nonbank_rev / 1e6)],
    ["Банковские (зарплатный проект, карта)", f1(bank_core / 1e6)],
    ["Ядро без эквайринга", f1(core / 1e6)],
    ["Эквайринг (низкий сценарий)", f1(acq_low / 1e6)],
    ["Эквайринг (высокий сценарий)", f1(acq_high / 1e6)],
    ["Всего (низкий - высокий)", f"{f1((core + acq_low) / 1e6)} - {f1((core + acq_high) / 1e6)}"],
])
share_of_spend = nonbank_rev / covered_final
p(f"Небанковская выручка на охваченного клиента: {share_of_spend:,.0f} ₽/год "
  f"({share_of_spend / 40_000:.0%}-{share_of_spend / 35_000:.0%} от расходов 35-40 тыс. ₽).".replace(",", " "))
p()

# ---------- 6. Новые клиенты ----------
org_msk = REG_MO_ORG * LEGAL_ENTITIES_MSK / LEGAL_ENTITIES_MO
flow_total = REG_MO_ORG + REG_MO_IP + org_msk       # оценка потока (ИП Москвы не включены)
flow_trade = flow_total * TRADE_SHARE
p("## 6. Новые клиенты (торговля)")
p(f"Организаций Москвы (оценка по численности юрлиц): {n0(org_msk)}")
p(f"Поток регистраций Москва + МО (без ИП Москвы): {n0(flow_total)}; в торговле (28,9%): {n0(flow_trade)}")
p()
core_new = 0.0
for prod, share in NEW_BASKET.items():
    if prod in PAID and prod != "Эквайринг":
        pay_share, price = PAID[prod]
        core_new += share * pay_share * price
new_total = sum(NEW_BASKET.values())
p(f"Сумма корзины новых клиентов: {f2(new_total)} (цель 4,0).")
p(f"Ядро (без эквайринга), ₽/год на клиента: {n0(core_new)}")
rows = []
for name, share in NEW_CLIENTS_PER_YEAR_SHARE.items():
    n = flow_trade * share
    c = n * core_new / 1e6
    a_lo = n * NEW_BASKET["Эквайринг"] * ACQ_LOW / 1e6
    a_hi = n * NEW_BASKET["Эквайринг"] * ACQ_HIGH / 1e6
    rows.append([name, f"{n:,.0f}".replace(",", " "), f1(c), f"{f1(a_lo)} - {f1(a_hi)}",
                 f"{f1(c + a_lo)} - {f1(c + a_hi)}"])
table(["Доля привлечения", "Новых клиентов/год", "Ядро, млн ₽", "Эквайринг, млн ₽", "Всего, млн ₽"], rows)

# траектория новых: приходят равномерно с 3-го по 18-й месяц, выход на цель за 12 мес.
arr = list(range(3, 19))
prog = [min(1.0, (18 - a) / RAMP_MONTHS_NEW) for a in arr]
avg_new = NEW_START + (NEW_TARGET - NEW_START) * sum(prog) / len(prog)
reached = sum(1 for x in prog if x >= 1.0) / len(prog)
p(f"Новые клиенты, месяц 18: среднее {f2(avg_new)} по всем когортам; достигли 4 продуктов {reached:.0%} клиентов.")
p()

# ---------- 7. Чувствительность ----------
p("## 7. Чувствительность ядра (млн ₽/год)")
rows = []
for u in (0.6, 0.8, 1.0):
    r, _ = economics(users_factor=u)
    rows.append([f"Реальное использование {u:.0%} плана", f1(sum(v[3] for v in r.values()) / 1e6)])
for c in (0.25, 0.40, 0.60):
    r, _ = economics(coverage=c)
    rows.append([f"Охват активных {c:.0%}", f1(sum(v[3] for v in r.values()) / 1e6)])
r, _ = economics(nonbank_scale=1.0 / tgt_non)
rows.append(["Небанковские 1,0 вместо 1,6 (цель 4,4, не 5)", f1(sum(v[3] for v in r.values()) / 1e6)])
table(["Сценарий", "Ядро"], rows)
r, a = economics(acq=ACQ_HIGH / 2)
p(f"Эквайринг при вдвое меньшем доходе на клиента: {f1(a / 1e6)} млн ₽ (высокий сценарий {f1(acq_high / 1e6)}).")
p()

# ---------- 8. Масштаб на Россию ----------
k = RUSSIA_TRADE / trade
p("## 8. Масштаб на Россию (торговля)")
p(f"Коэффициент к Москве и МО: x{f1(k)} (при тех же ценах, оборотах и охвате; допущение).")
p(f"Ядро: {f1(core * k / 1e9 * 1000)} млн ₽; с эквайрингом: "
  f"{f1((core + acq_low) * k / 1e9 * 1000)} - {f1((core + acq_high) * k / 1e9 * 1000)} млн ₽/год.")
p()

# ---------- 9. Нагрузка менеджеров ----------
delta_mgr = sum(BASKET[x][2] - BASKET[x][1] for x in MANAGER_HANDLED)
conn_total = covered_final * delta_mgr
conn_month = conn_total / 12
managers = trade / CLIENTS_PER_MANAGER
per_mgr = conn_month / managers
hours = per_mgr * HOURS_PER_CONNECTION
p("## 9. Нагрузка менеджеров")
table(["Показатель", "Значение"], [
    ["Доля прироста через менеджера", f"{delta_mgr / delta:.0%} ({f2(delta_mgr)} из {f2(delta)})"],
    ["Подключений с менеджером за период, тыс.", f1(conn_total / 1000)],
    ["В месяц (12 месяцев), тыс.", f1(conn_month / 1000)],
    ["Менеджеров (эквивалент)", f"{managers:,.0f}"],
    ["Подключений на менеджера в месяц", f1(per_mgr)],
    ["Часов в месяц (2 ч на подключение)", f1(hours)],
    ["Доля рабочего времени (150 ч/мес.)", f"{hours / HOURS_PER_MONTH:.1%}".replace(".", ",")],
])

Path(__file__).with_name("RESULTS.generated.md").write_text("\n".join(out) + "\n", encoding="utf-8")

# ---------- Ключевые цифры для проверки документов ----------
a18, cov18 = avg_covered(18)
seg18 = START_AVG + (a18 - START_AVG) * cov18
n10 = flow_trade * NEW_CLIENTS_PER_YEAR_SHARE["10%"]
core_new_10 = n10 * core_new / 1e6
acq_new_lo = n10 * NEW_BASKET["Эквайринг"] * ACQ_LOW / 1e6
acq_new_hi = n10 * NEW_BASKET["Эквайринг"] * ACQ_HIGH / 1e6
KEY = {
    "trade_clients": n0(trade),
    "active_clients": n0(active),
    "covered_clients": n0(covered_final),
    "start_avg": f2(START_AVG),
    "target_avg": f2(tgt_total),
    "bank_target": f2(tgt_bank),
    "avg_covered_m18": f2(a18),
    "avg_segment_m18": f2(seg18),
    "avg_base_after": f2(START_AVG + extra_products / BASE),
    "extra_products": n0(extra_products),
    "core_existing": f1(core / 1e6),
    "nonbank_existing": f1(nonbank_rev / 1e6),
    "core_new_10": f1(core_new_10),
    "core_total": f"{core / 1e6 + core_new_10:,.0f}".replace(",", " "),
    "total_low": f"{core / 1e6 + acq_low / 1e6 + core_new_10 + acq_new_lo:,.0f}".replace(",", " "),
    "total_high": f"{core / 1e6 + acq_high / 1e6 + core_new_10 + acq_new_hi:,.0f}".replace(",", " "),
    "acq_existing_low": f1(acq_low / 1e6),
    "acq_existing_high": f1(acq_high / 1e6),
    "manager_share_time": f"{hours / HOURS_PER_MONTH:.1%}".replace(".", ","),
}
Path(__file__).with_name("key_figures.json").write_text(
    json.dumps(KEY, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
