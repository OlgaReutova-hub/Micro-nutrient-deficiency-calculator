# Скилл: создание Streamlit-калькулятора нутриентов

Руководство по созданию аналогичного веб-приложения — калькулятора поступления микро- и макронутриентов на типовых рационах. Приложение строится на Streamlit, данные хранятся в JSON, расчёт — эвристический (без API и ML).

---

## Что представляет собой приложение

Пользователь выбирает:
- пол (женщина / мужчина),
- калорийность рациона (несколько уровней),
- тип меню (домашнее / офисное / другие варианты).

Приложение показывает:
- перечень блюд по приёмам пищи (завтрак, обед, перекус, ужин),
- панель макро- и микронутриентов с прогресс-барами и цветовой индикацией относительно суточных норм.

---

## Структура файлов

```
project/
├── app.py                          # точка входа Streamlit
├── requirements.txt                # streamlit>=1.44.0
├── .streamlit/
│   └── config.toml                 # цветовая тема
└── data/
    └── menu_extended_nutrients.json  # сценарии меню + нутриентные профили
```

Вспомогательные скрипты (опционально):
```
scripts/
├── generate_extended_menu_json.py  # пересборка JSON из исходного файла
└── export_menus_md.py              # экспорт меню в Markdown
```

---

## Шаг 1 — Подготовка данных (JSON)

### Структура JSON-файла

```json
{
  "meta": {
    "nutrient_norms": { ... },
    "nutrient_labels": { ... },
    "indicator_logic": { ... }
  },
  "scenarios": [ ... ]
}
```

### meta.nutrient_norms

Нормы потребления. Если норма одинакова для обоих полов — число. Если разная — объект `{"female": X, "male": Y}`. Жиры и углеводы вычисляются из калорийности:

```json
"nutrient_norms": {
  "protein_g":        {"female": 60, "male": 75},
  "fiber_g":          {"female": 25, "male": 30},
  "vitamin_a_mcg":    {"female": 800, "male": 900},
  "iron_mg":          {"female": 18, "male": 10},
  "vitamin_b1_mg":    1.5,
  "vitamin_b2_mg":    1.8,
  "vitamin_b6_mg":    2.0,
  "niacin_b3_mg":     20,
  "vitamin_b12_mcg":  3,
  "folate_mcg":       400,
  "pantothenic_acid_mg": 5,
  "vitamin_c_mg":     100,
  "vitamin_d_mcg":    15,
  "vitamin_e_mg":     15,
  "vitamin_k_mcg":    120,
  "calcium_mg":       1000,
  "phosphorus_mg":    700,
  "magnesium_mg":     420,
  "potassium_mg":     3500,
  "sodium_mg":        1300,
  "zinc_mg":          12,
  "iodine_mcg":       150,
  "copper_mg":        1,
  "manganese_mg":     2,
  "fat_g":            "kcal * 0.30 / 9",
  "carbs_g":          "kcal * 0.45 / 4",
  "cholesterol_mg":   300
}
```

Источник норм: **МР 2.3.1.0253-21** (Роспотребнадзор, 22.07.2021).

### meta.nutrient_labels

Словарь «ключ → русское название»:

```json
"nutrient_labels": {
  "protein_g":           "Белок",
  "fat_g":               "Жиры",
  "carbs_g":             "Углеводы",
  "cholesterol_mg":      "Холестерин",
  "fiber_g":             "Пищевые волокна",
  "vitamin_a_mcg":       "Витамин A",
  "vitamin_b1_mg":       "Витамин B1",
  "vitamin_b2_mg":       "Витамин B2",
  "vitamin_b6_mg":       "Витамин B6",
  "niacin_b3_mg":        "Ниацин (B3)",
  "vitamin_b12_mcg":     "Витамин B12",
  "folate_mcg":          "Фолаты",
  "pantothenic_acid_mg": "Пантотеновая кислота",
  "vitamin_c_mg":        "Витамин C",
  "vitamin_d_mcg":       "Витамин D",
  "vitamin_e_mg":        "Витамин E",
  "vitamin_k_mcg":       "Витамин K",
  "calcium_mg":          "Кальций",
  "phosphorus_mg":       "Фосфор",
  "magnesium_mg":        "Магний",
  "potassium_mg":        "Калий",
  "sodium_mg":           "Натрий",
  "iron_mg":             "Железо",
  "zinc_mg":             "Цинк",
  "iodine_mcg":          "Йод",
  "copper_mg":           "Медь",
  "manganese_mg":        "Марганец"
}
```

### Один сценарий

```json
{
  "id": "1200_office",
  "kcal": 1200,
  "meal_type": "office",
  "meal_type_label": "Офисное меню",
  "title": "Меню на день",
  "meals": {
    "breakfast": ["Кофе с молоком (250 мл)", "Круассан (55 г)"],
    "lunch":     ["Салат с курицей (180 г)", "Суп куриный (300 г)"],
    "snack":     ["Йогурт питьевой (250 мл)"],
    "dinner":    ["Куриная грудка (130 г)", "Пюре картофельное (180 г)"]
  },
  "nutrients_actual": {
    "protein_g": 48.0,
    "fat_g": 46.7,
    ...
  },
  "deficits": {
    "protein_g": {
      "label": "Белок",
      "actual": 48.0,
      "norm_female": 60.0,
      "norm_male": 75.0,
      "female_percent": 80,
      "male_percent": 64,
      "female_deficit_percent": 20,
      "male_deficit_percent": 36,
      "female_indicator": "yellow",
      "male_indicator": "yellow"
    },
    ...
  }
}
```

**Правило indicator:** `green` ≥ 90 %, `yellow` 60–89 %, `red` < 60 %.

---

## Шаг 2 — Генерация нутриентных профилей (скрипт)

Скрипт `generate_extended_menu_json.py` принимает базовый JSON с меню и дописывает `nutrients_actual` и `deficits` через эвристику:

```python
MEAL_TYPE_FACTOR = {"home": 1.08, "office": 1.0, "city_snack": 0.88}
PROTEIN_SHARE    = {"home": 0.042, "office": 0.040, "city_snack": 0.038}
FAT_KCAL_SHARE   = {"home": 0.32, "office": 0.35, "city_snack": 0.28}
CARB_KCAL_SHARE  = {"home": 0.40, "office": 0.44, "city_snack": 0.38}
CHOL_MG_PER_KCAL = {"home": 0.12, "office": 0.22, "city_snack": 0.16}

def estimate_nutrients(scenario):
    kcal = scenario["kcal"]
    mt = scenario["meal_type"]
    f = MEAL_TYPE_FACTOR[mt]
    fiber_g = scenario.get("nutrients_actual", {}).get("fiber_g", 12)
    iron_mg = scenario.get("nutrients_actual", {}).get("iron_mg", 9)

    return {
        "protein_g":           round(kcal * PROTEIN_SHARE[mt], 1),
        "fat_g":               round(kcal * FAT_KCAL_SHARE[mt] / 9, 1),
        "carbs_g":             round(kcal * CARB_KCAL_SHARE[mt] / 4, 1),
        "cholesterol_mg":      round(kcal * CHOL_MG_PER_KCAL[mt], 1),
        "fiber_g":             fiber_g,
        "vitamin_a_mcg":       round((320 + kcal * 0.18) * f, 1),
        "vitamin_b1_mg":       round((0.45 + kcal / 3000) * f, 1),
        "vitamin_b2_mg":       round((0.65 + kcal / 2600) * f, 1),
        "vitamin_b6_mg":       round((0.7 + kcal / 2800) * f, 1),
        "niacin_b3_mg":        round((7 + kcal / 250) * f, 1),
        "vitamin_b12_mcg":     round((1.2 + kcal / 1700) * f, 1),
        "folate_mcg":          round((115 + fiber_g * 9) * f, 1),
        "pantothenic_acid_mg": round((2.0 + kcal / 1700) * f, 1),
        "vitamin_c_mg":        round((22 + fiber_g * 2.1) * f, 1),
        "vitamin_d_mcg":       round((2.0 + kcal / 1000) * (1.2 if mt == "home" else 1.0), 1),
        "vitamin_e_mg":        round((4.0 + kcal / 500) * f, 1),
        "vitamin_k_mcg":       round((35 + fiber_g * 3.2) * f, 1),
        "calcium_mg":          round((430 + kcal * 0.18) * f, 1),
        "phosphorus_mg":       round((610 + kcal * 0.16) * f, 1),
        "magnesium_mg":        round((120 + fiber_g * 7.5) * f, 1),
        "potassium_mg":        round((1050 + fiber_g * 95) * f, 1),
        "sodium_mg":           round(950 + kcal * {"home": 0.22, "office": 0.32, "city_snack": 0.42}[mt], 1),
        "iron_mg":             iron_mg,
        "zinc_mg":             round((4.2 + kcal / 520) * f, 1),
        "iodine_mcg":          round((55 + kcal / 35) * f, 1),
        "copper_mg":           round((0.45 + fiber_g / 45) * f, 1),
        "manganese_mg":        round((0.8 + fiber_g / 18) * f, 1),
    }
```

После этого вызывается `build_deficits()`, которая по каждому нутриенту вычисляет `norm_female`, `norm_male`, `female_percent`, `male_percent`, `*_indicator`.

---

## Шаг 3 — Настройка темы (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#2e7d32"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#e8f5e9"
textColor = "#1b3320"
font = "sans serif"

[server]
headless = true
```

Замените `primaryColor` на акцентный цвет вашего проекта.

---

## Шаг 4 — Структура app.py

### Константы

```python
ACCENT       = "#2e7d32"   # основной цвет
ACCENT_DARK  = "#1b5e20"   # тёмный акцент (заголовки, нажатая кнопка)
ACCENT_LIGHT = "#e8f5e9"   # фоновый пастельный
BTN_OUTLINE  = "#a5d6a7"   # рамка кнопки в idle-состоянии
BTN_IDLE_BG  = "rgba(232, 245, 233, 0.55)"

KCAL_OPTIONS = [(1200, "1200 ккал"), (1500, "1500 ккал"), ...]  # (значение, метка)
MENU_OPTIONS = [("home", "Домашнее"), ("office", "Офисное"), ...]

MEAL_LABELS  = {"breakfast": "Завтрак", "lunch": "Обед", ...}

MACRO_KEYS   = ("protein_g", "fat_g", "carbs_g", "fiber_g", "cholesterol_mg")
# micro_keys вычисляется динамически: все ключи из nutrient_labels кроме MACRO_KEYS
```

### Session state

```python
def init_session_state():
    defaults = {"gender": "female", "kcal": None, "meal_type": None, "show_menu": False}
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
```

При смене пола или типа параметра `show_menu` сбрасывается в `False`, чтобы результаты обновлялись только после повторного нажатия кнопки.

### Кнопки-переключатели (outline toggle)

Стандартные `st.button` стилизуются через `st.markdown` с динамическим CSS по ключу виджета:

```python
def style_outline_button(widget_key, selected):
    bg     = ACCENT if selected else BTN_IDLE_BG
    color  = "#ffffff" if selected else "#212121"
    border = f"2px solid {ACCENT_DARK}" if selected else f"1.5px solid {BTN_OUTLINE}"
    shadow = "0 3px 10px rgba(46,125,50,0.3)" if selected else "none"
    st.markdown(
        f"<style>.st-key-{widget_key} button{{"
        f"background:{bg}!important;color:{color}!important;"
        f"border:{border}!important;box-shadow:{shadow}!important;}}</style>",
        unsafe_allow_html=True,
    )

def render_outline_choice_row(label, options, state_key):
    st.markdown(f'<p class="section-label">{label}</p>', unsafe_allow_html=True)
    cols = st.columns(len(options))
    for col, (value, text) in zip(cols, options):
        key = f"{state_key}_{value}"
        selected = st.session_state.get(state_key) == value
        style_outline_button(key, selected)
        with col:
            st.button(text, key=key, use_container_width=True,
                      on_click=lambda v=value: _select_option(state_key, v))

def _select_option(state_key, value):
    st.session_state[state_key] = value
    st.session_state.show_menu = False
```

### Панель нутриентов (HTML)

Нутриенты рендерятся через `st.html()` — это избегает лишних перерисовок Streamlit:

```python
def build_nutrient_rows_html(scenario, gender, nutrient_keys):
    parts = []
    for key in nutrient_keys:
        entry = scenario["deficits"].get(key)
        if not entry:
            continue
        percent   = min(entry[f"{gender}_percent"], 150)
        bar_width = min(percent, 100)
        color     = INDICATOR_COLORS[entry[f"{gender}_indicator"]]
        unit      = format_unit(key)   # "г" / "мг" / "мкг"
        parts.append(
            f'<div class="nutrient-row">'
            f'<span class="nutrient-name">{entry["label"]}</span>'
            f'<span class="nutrient-value">{entry["actual"]:g} {unit} · {percent}%</span>'
            f'<div class="nutrient-bar-wrap">'
            f'<div class="nutrient-bar" style="width:{bar_width}%;background:{color};"></div>'
            f"</div></div>"
            f'<div class="nutrient-norm">норма: {entry[f"norm_{gender}"]:g} {unit}</div>'
        )
    return "".join(parts)
```

`format_unit` определяет единицу по суффиксу ключа:
- `_g` → "г", `_mg` → "мг", `_mcg` → "мкг"

### Двухколоночный макет результата

```python
col_menu, col_nutrients = st.columns([1.1, 1], gap="large")

with col_menu:
    st.markdown(f"### {scenario['title']}")
    st.html(render_menu(scenario))   # карточки блюд

with col_nutrients:
    st.markdown("### Макро- и микронутриенты")
    st.html(build_nutrients_panel_html(scenario, gender, MACRO_KEYS, micro_keys))
    # легенда цветов
```

### Кнопка «Показать меню»

Блокируется, пока не выбраны все параметры:

```python
def all_selected():
    return (st.session_state.gender is not None
            and st.session_state.kcal is not None
            and st.session_state.meal_type is not None)

clicked = st.button("Показать меню", key="show_menu_btn",
                    disabled=not all_selected())
if clicked and all_selected():
    st.session_state.show_menu = True
```

---

## Шаг 5 — Как адаптировать под новую тему

| Что менять | Где |
|---|---|
| Акцентный цвет | `ACCENT`, `ACCENT_DARK`, `ACCENT_LIGHT`, `config.toml` |
| Уровни калорийности | `KCAL_OPTIONS` |
| Типы меню | `MENU_OPTIONS`, `MEAL_TYPE_FACTOR` в скрипте |
| Нормы нутриентов | `NORMS` в скрипте, `nutrient_norms` в JSON |
| Список нутриентов | `LABELS` + `MACRO_KEYS` |
| Эвристики расчёта | функция `estimate_nutrients` в скрипте |
| Блюда | секция `meals` каждого сценария в JSON |
| Источник норм | текст дисклеймера `MENU_DISCLAIMER` |

---

## Шаг 6 — Запуск и деплой

### Локально

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Community Cloud

1. Загрузить папку `github/` в репозиторий GitHub.
2. На share.streamlit.io указать `app.py` как main file.
3. `requirements.txt` и `.streamlit/config.toml` подтянутся автоматически.

---

## Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| `KeyError` при рендере нутриентов | ключ в `MACRO_KEYS` отсутствует в JSON | проверить соответствие ключей |
| Кнопка-toggle не меняет цвет | ключ `st-key-*` не совпадает с реальным | убедиться, что в `widget_key` нет пробелов и спецсимволов |
| `show_menu` не сбрасывается | забыт `st.session_state.show_menu = False` в `on_click` | добавить сброс во все обработчики |
| Проценты > 100% на баре | не применён `min(percent, 100)` к ширине | ширина бара = `min(percent, 100)`, процент в тексте = `min(percent, 150)` |
| JSON не валидируется | у части сценариев нет всех ключей нутриентов | запустить `validate_json()` из скрипта-генератора |

---

## Минимальный чеклист для нового калькулятора

- [ ] Определить нутриенты и нормы (MACRO + MICRO)
- [ ] Составить список сценариев (kcal × meal_type) и блюда для каждого
- [ ] Заполнить `nutrients_actual` (вручную или через скрипт-эвристику)
- [ ] Сгенерировать `deficits` скриптом и провалидировать JSON
- [ ] Заменить акцентный цвет в `config.toml` и константах `app.py`
- [ ] Обновить `KCAL_OPTIONS`, `MENU_OPTIONS`, `MEAL_LABELS`, `MACRO_KEYS`
- [ ] Проверить `format_unit` — все суффиксы ключей должны быть известны
- [ ] Запустить приложение локально и пройти все комбинации параметров
- [ ] Обновить `MENU_DISCLAIMER` с актуальным источником норм
