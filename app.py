"""Калькулятор дефицита микронутриентов на низкокалорийной диете."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "menu_1200_2000_extended_nutrients.json"

ACCENT = "#2e7d32"
ACCENT_DARK = "#1b5e20"
ACCENT_LIGHT = "#e8f5e9"
BTN_OUTLINE = "#a5d6a7"
BTN_IDLE_BG = "rgba(232, 245, 233, 0.55)"

KCAL_OPTIONS = [
    (1200, "1200 ккал"),
    (1500, "1500 ккал"),
    (1800, "1800 ккал"),
    (2000, "2000 ккал"),
]

MENU_OPTIONS = [
    ("home", "Домашнее меню"),
    ("office", "Офисное меню"),
    ("city_snack", "Перекус в городе"),
]

MEAL_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "snack": "Перекус",
    "dinner": "Ужин",
}

MACRO_KEYS = ("protein_g", "fat_g", "carbs_g", "fiber_g", "cholesterol_mg")

INDICATOR_COLORS = {
    "green": "#2e7d32",
    "yellow": "#f9a825",
    "red": "#c62828",
}

INDICATOR_LOGIC = {
    "green": "поступление ≥ 90% от нормы",
    "yellow": "поступление 60–89% от нормы",
    "red": "поступление < 60% от нормы",
}

MENU_DISCLAIMER = (
    "Значения — демонстрационные усреднённые оценки по типовым блюдам.\n\n"
    "Нормы потребления микро- и макронутриентов — Методические рекомендации "
    'MP 2.3.1.0253-21 «Нормы физиологических потребностей в энергии и пищевых '
    'веществах для различных групп населения Российской Федерации» '
    "(утв. Федеральной службой по надзору в сфере защиты прав потребителей "
    "и благополучия человека 22 июля 2021 г.)."
)


@lru_cache(maxsize=1)
def load_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def init_session_state() -> None:
    defaults = {
        "gender": "female",
        "kcal": None,
        "meal_type": None,
        "show_menu": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap');

        .stApp {{
            background: linear-gradient(180deg, #f1f8f4 0%, #ffffff 240px);
            font-family: 'Manrope', sans-serif;
        }}

        [data-testid="stHeader"] {{
            background: rgba(241, 248, 244, 0.9);
        }}

        .app-heading {{
            color: {ACCENT_DARK};
            font-size: clamp(1.75rem, 3.8vw, 2.5rem);
            font-weight: 700;
            margin: 0 0 1.25rem 0;
            line-height: 1.25;
        }}

        .app-heading span {{
            display: block;
            color: {ACCENT_DARK};
            font-size: clamp(1.35rem, 2.8vw, 1.9rem);
            font-weight: 700;
            line-height: 1.2;
            margin-top: 0.15rem;
        }}

        @media (max-width: 768px) {{
            .app-heading {{
                font-size: clamp(2rem, 7.2vw, 2.65rem);
                line-height: 1.2;
            }}

            .app-heading span {{
                font-size: clamp(1.6rem, 5.8vw, 2rem);
                margin-top: 0.2rem;
            }}
        }}

        .menu-disclaimer {{
            font-size: 0.78rem;
            color: #607d8b;
            line-height: 1.45;
            margin-top: 0.75rem;
        }}

        .section-label {{
            color: #212121;
            font-weight: 600;
            font-size: 0.95rem;
            margin: 0.75rem 0 0.45rem 0;
        }}

        .menu-card {{
            background: #ffffff;
            border: 1px solid #c8e6c9;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 2px 8px rgba(46, 125, 50, 0.08);
        }}

        .menu-card h4 {{
            color: {ACCENT};
            margin: 0 0 0.5rem 0;
            font-size: 1rem;
        }}

        .menu-card ul {{
            margin: 0;
            padding-left: 1.15rem;
            color: #2f3d33;
        }}

        .nutrients-panel {{
            background: #ffffff;
            border: 1px solid #c8e6c9;
            border-radius: 12px;
            padding: 0.85rem 1rem;
        }}

        .nutrients-panel h4 {{
            color: {ACCENT_DARK};
            font-size: 0.95rem;
            margin: 0.75rem 0 0.5rem 0;
            font-weight: 700;
        }}

        .nutrients-panel h4:first-child {{
            margin-top: 0;
        }}

        .nutrient-row {{
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 0.35rem 0.75rem;
            align-items: center;
            margin-bottom: 0.15rem;
            font-size: 0.88rem;
        }}

        .nutrient-name {{
            color: #37474f;
        }}

        .nutrient-value {{
            color: {ACCENT_DARK};
            font-weight: 600;
            white-space: nowrap;
        }}

        .nutrient-bar-wrap {{
            grid-column: 1 / -1;
            height: 7px;
            background: #e8f5e9;
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 0.1rem;
        }}

        .nutrient-bar {{
            height: 100%;
            border-radius: 999px;
        }}

        .nutrient-norm {{
            font-size: 0.75rem;
            color: #78909c;
            margin: 0 0 0.55rem 0;
        }}

        .summary-pill {{
            display: inline-block;
            background: {ACCENT_LIGHT};
            color: {ACCENT_DARK};
            border: 1px solid #a5d6a7;
            border-radius: 999px;
            padding: 0.35rem 0.75rem;
            margin: 0.15rem 0.35rem 0.15rem 0;
            font-size: 0.82rem;
            font-weight: 600;
        }}

        .hint-box {{
            background: #fff8e1;
            border-left: 4px solid #f9a825;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            color: #5d4037;
            font-size: 0.9rem;
            margin: 0.5rem 0 1rem 0;
        }}

        div[data-testid="stButton"] > button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: transform 0.12s ease, box-shadow 0.12s ease !important;
        }}

        .st-key-show_menu_btn button {{
            background: {ACCENT} !important;
            color: #ffffff !important;
            border: 2px solid {ACCENT_DARK} !important;
            padding: 0.7rem 1.5rem !important;
            font-size: 1.05rem !important;
            box-shadow: 0 4px 14px rgba(46, 125, 50, 0.35) !important;
        }}

        .st-key-show_menu_btn button:hover {{
            background: {ACCENT_DARK} !important;
            transform: translateY(-1px);
        }}

        .st-key-show_menu_btn button:disabled {{
            background: #c8e6c9 !important;
            color: #ffffff !important;
            border-color: #a5d6a7 !important;
            box-shadow: none !important;
            opacity: 1 !important;
        }}

        div[data-testid="stRadio"] > label {{
            display: none;
        }}

        div[data-testid="stRadio"] > div {{
            flex-direction: row !important;
            gap: 2rem;
        }}

        div[data-testid="stRadio"] label[data-baseweb="radio"] {{
            background: transparent !important;
        }}

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{
            background-color: #ffffff !important;
            border: 2px solid #bdbdbd !important;
        }}

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {{
            background-color: {ACCENT} !important;
            border-color: {ACCENT_DARK} !important;
        }}

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {{
            background-color: #ffffff !important;
        }}

        div[data-testid="stRadio"] label span {{
            color: #212121 !important;
            font-weight: 500 !important;
            font-size: 1rem !important;
        }}

        @media (max-width: 768px) {{
            .nutrient-row {{
                font-size: 0.84rem;
            }}
            .menu-card {{
                padding: 0.85rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_outline_button(widget_key: str, selected: bool) -> None:
    if selected:
        bg = ACCENT
        color = "#ffffff"
        border = f"2px solid {ACCENT_DARK}"
        shadow = "0 3px 10px rgba(46, 125, 50, 0.3)"
    else:
        bg = BTN_IDLE_BG
        color = "#212121"
        border = f"1.5px solid {BTN_OUTLINE}"
        shadow = "none"
    st.markdown(
        f"<style>.st-key-{widget_key} button{{background:{bg}!important;color:{color}!important;"
        f"border:{border}!important;box-shadow:{shadow}!important;}}</style>",
        unsafe_allow_html=True,
    )


def _select_option(state_key: str, value: object) -> None:
    st.session_state[state_key] = value
    st.session_state.show_menu = False


def render_outline_choice_row(
    label: str,
    options: list[tuple],
    state_key: str,
) -> None:
    st.markdown(f'<p class="section-label">{label}</p>', unsafe_allow_html=True)
    cols = st.columns(len(options))
    for col, (value, text) in zip(cols, options):
        widget_key = f"{state_key}_{value}"
        selected = st.session_state.get(state_key) == value
        style_outline_button(widget_key, selected)
        with col:
            st.button(
                text,
                key=widget_key,
                use_container_width=True,
                on_click=_select_option,
                args=(state_key, value),
            )


def render_gender_radio() -> None:
    st.markdown('<p class="section-label">Пол</p>', unsafe_allow_html=True)
    gender_labels = {"female": "Женщина", "male": "Мужчина"}

    def on_gender_change() -> None:
        st.session_state.show_menu = False

    st.radio(
        "Пол",
        options=list(gender_labels.keys()),
        format_func=lambda x: gender_labels[x],
        horizontal=True,
        label_visibility="collapsed",
        key="gender",
        on_change=on_gender_change,
    )


def find_scenario(data: dict, kcal: int, meal_type: str) -> dict | None:
    for scenario in data["scenarios"]:
        if scenario["kcal"] == kcal and scenario["meal_type"] == meal_type:
            return scenario
    return None


def get_norm(deficit_entry: dict, gender: str) -> float:
    return float(deficit_entry.get(f"norm_{gender}", 0))


def get_percent(deficit_entry: dict, gender: str) -> int:
    return int(deficit_entry.get(f"{gender}_percent", 0))


def indicator_from_percent(percent: int) -> str:
    if percent >= 90:
        return "green"
    if percent >= 60:
        return "yellow"
    return "red"


def get_indicator(deficit_entry: dict, gender: str) -> str:
    return indicator_from_percent(get_percent(deficit_entry, gender))


def format_unit(key: str) -> str:
    if key.endswith("_g"):
        return "г"
    if key.endswith("_mg"):
        return "мг"
    if key.endswith("_mcg"):
        return "мкг"
    return ""


def build_nutrient_rows_html(
    scenario: dict,
    gender: str,
    nutrient_keys: tuple[str, ...],
) -> str:
    parts: list[str] = []
    for key in nutrient_keys:
        entry = scenario["deficits"].get(key)
        if not entry:
            continue
        percent = min(get_percent(entry, gender), 150)
        bar_width = min(percent, 100)
        color = INDICATOR_COLORS.get(get_indicator(entry, gender), ACCENT)
        unit = format_unit(key)
        norm = get_norm(entry, gender)
        actual = entry["actual"]
        label = entry["label"]
        parts.append(
            f'<div class="nutrient-row">'
            f'<span class="nutrient-name">{label}</span>'
            f'<span class="nutrient-value">{actual:g} {unit} · {percent}%</span>'
            f'<div class="nutrient-bar-wrap">'
            f'<div class="nutrient-bar" style="width:{bar_width}%;background:{color};"></div>'
            f"</div></div>"
            f'<div class="nutrient-norm">норма: {norm:g} {unit}</div>'
        )
    return "".join(parts)


def build_nutrients_panel_html(
    scenario: dict,
    gender: str,
    macro_keys: tuple[str, ...],
    micro_keys: tuple[str, ...],
) -> str:
    macro_rows = build_nutrient_rows_html(scenario, gender, macro_keys)
    micro_rows = build_nutrient_rows_html(scenario, gender, micro_keys)
    return (
        '<div class="nutrients-panel">'
        "<h4>Макронутриенты</h4>"
        f"{macro_rows}"
        "<h4>Микронутриенты</h4>"
        f"{micro_rows}"
        "</div>"
    )


def render_menu(scenario: dict) -> str:
    blocks: list[str] = []
    for meal_key, meal_title in MEAL_LABELS.items():
        items = scenario["meals"].get(meal_key, [])
        if not items:
            continue
        li = "".join(f"<li>{item}</li>" for item in items)
        blocks.append(
            f'<div class="menu-card"><h4>{meal_title}</h4><ul>{li}</ul></div>'
        )
    return "".join(blocks)


def all_selected() -> bool:
    return (
        st.session_state.gender is not None
        and st.session_state.kcal is not None
        and st.session_state.meal_type is not None
    )


def main() -> None:
    st.set_page_config(
        page_title="Калькулятор микронутриентов",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session_state()
    inject_global_css()

    data = load_data()
    labels = data["meta"]["nutrient_labels"]
    micro_keys = tuple(k for k in labels if k not in MACRO_KEYS)

    st.markdown(
        '<h1 class="app-heading">Калькулятор поступления микронутриентов'
        '<span>на низкокалорийной диете</span></h1>',
        unsafe_allow_html=True,
    )

    render_gender_radio()
    render_outline_choice_row("Калорийность меню", KCAL_OPTIONS, "kcal")
    render_outline_choice_row("Тип меню", MENU_OPTIONS, "meal_type")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        show_clicked = st.button(
            "Показать меню",
            key="show_menu_btn",
            use_container_width=True,
            disabled=not all_selected(),
        )

    if show_clicked and all_selected():
        st.session_state.show_menu = True

    if not all_selected():
        with col_info:
            st.markdown(
                '<div class="hint-box">Выберите калорийность и тип меню, '
                "затем нажмите «Показать меню».</div>",
                unsafe_allow_html=True,
            )

    if st.session_state.show_menu and all_selected():
        scenario = find_scenario(
            data,
            st.session_state.kcal,
            st.session_state.meal_type,
        )
        if not scenario:
            st.error("Сценарий не найден для выбранных параметров.")
            return

        gender = st.session_state.gender
        gender_label = "женщина" if gender == "female" else "мужчина"
        menu_label = next(
            (lbl for val, lbl in MENU_OPTIONS if val == st.session_state.meal_type),
            "",
        )

        st.markdown(
            f'<span class="summary-pill">{st.session_state.kcal} ккал</span>'
            f'<span class="summary-pill">{menu_label}</span>'
            f'<span class="summary-pill">{gender_label}</span>',
            unsafe_allow_html=True,
        )

        col_menu, col_nutrients = st.columns([1.1, 1], gap="large")

        with col_menu:
            st.markdown(f"### {scenario['title']}")
            st.html(render_menu(scenario))
            st.markdown(
                f'<div class="menu-disclaimer">{MENU_DISCLAIMER.replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True,
            )

        with col_nutrients:
            st.markdown("### Макро- и микронутриенты")
            nutrients_html = build_nutrients_panel_html(
                scenario, gender, MACRO_KEYS, micro_keys
            )
            st.html(nutrients_html)

            st.markdown(
                "<div style='font-size:0.8rem;color:#607d8b;margin-top:0.5rem;'>"
                f"🟢 {INDICATOR_LOGIC['green']} · "
                f"🟡 {INDICATOR_LOGIC['yellow']} · "
                f"🔴 {INDICATOR_LOGIC['red']}"
                "</div>",
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
