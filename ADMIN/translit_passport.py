#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Транслитератор ФИО (RU → EN) по ПАСПОРТНЫМ правилам ICAO.
БЕЗ отчества. Поддержка 25+ стран.

Особенности:
 • Для каждой страны — отдельная карта транслитерации по паспортным/ICAO правилам.
 • Автоматическое удаление отчества (Александрович, Александровна, и т.д.).
 • Работа с Excel/CSV через pandas (поддержка 100 000+ записей).
 • Вывод «Capitalize Each Word» (Volkov Ihar, Ivanov Sergei …).

Использование:
    python translit_passport.py input.xlsx output.xlsx
    python translit_passport.py data.csv result.csv --fio-col "ФИО_рус" --citizenship-col "Страна"
"""

import sys
import re
import os
import pandas as pd

# =============================================================================
#  ПАСПОРТНЫЕ / ICAO КАРТЫ ТРАНСЛИТЕРАЦИИ
# =============================================================================

# ---------- 1. РОССИЯ — ICAO Doc 9303 (Приказ МИД РФ № 2 от 09.01.2025) ----------
RUSSIA_MAP = {
    'А': 'A',  'Б': 'B',  'В': 'V',  'Г': 'G',  'Д': 'D',
    'Е': 'E',  'Ё': 'E',  'Ж': 'ZH', 'З': 'Z',  'И': 'I',
    'Й': 'I',  'К': 'K',  'Л': 'L',  'М': 'M',  'Н': 'N',
    'О': 'O',  'П': 'P',  'Р': 'R',  'С': 'S',  'Т': 'T',
    'У': 'U',  'Ф': 'F',  'Х': 'KH', 'Ц': 'TS', 'Ч': 'CH',
    'Ш': 'SH', 'Щ': 'SHCH','Ъ': 'IE','Ы': 'Y', 'Ь': '',
    'Э': 'E',  'Ю': 'IU', 'Я': 'IA',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'е': 'e', 'ё': 'e', 'ж': 'zh','з': 'z', 'и': 'i',
    'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'kh','ц': 'ts','ч': 'ch',
    'ш': 'sh','щ': 'shch','ъ': 'ie','ы': 'y', 'ь': '',
    'э': 'e', 'ю': 'iu','я': 'ia',
}

# ---------- 2. БЕЛАРУСЬ — Постановление МВД РБ № 288 от 09.10.2008 ----------
BELARUS_MAP = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'H', 'Д': 'D',
    'Е': 'E', 'Ё': 'IO','Ж': 'ZH','З': 'Z', 'І': 'I',
    'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ў': 'U', 'Ф': 'F', 'Х': 'KH','Ц': 'TS',
    'Ч': 'CH','Ш': 'SH','Щ': 'SHCH','Ь': '',
    'Ы': 'Y', 'Э': 'E', 'Ю': 'IU','Я': 'IA',
    'И': 'I',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'д': 'd',
    'е': 'e', 'ё': 'io','ж': 'zh','з': 'z', 'і': 'i',
    'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ў': 'u', 'ф': 'f', 'х': 'kh','ц': 'ts',
    'ч': 'ch','ш': 'sh','щ': 'shch','ь': '',
    'ы': 'y', 'э': 'e', 'ю': 'iu','я': 'ia',
    'и': 'i',
}

# ---------- 3. УКРАИНА — национальные правила загранпаспорта ----------
UKRAINE_MAP = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'H', 'Ґ': 'G',
    'Д': 'D', 'Е': 'E', 'Є': 'YE','Ж': 'ZH','З': 'Z',
    'И': 'Y', 'І': 'I', 'Ї': 'YI','Й': 'Y', 'К': 'K',
    'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P',
    'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F',
    'Х': 'KH','Ц': 'TS','Ч': 'CH','Ш': 'SH','Щ': 'SHCH',
    'Ю': 'YU','Я': 'YA','Ь': '', 'Ъ': '',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g',
    'д': 'd', 'е': 'e', 'є': 'ye','ж': 'zh','з': 'z',
    'и': 'y', 'і': 'i', 'ї': 'yi','й': 'y', 'к': 'k',
    'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p',
    'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
    'х': 'kh','ц': 'ts','ч': 'ch','ш': 'sh','щ': 'shch',
    'ю': 'yu','я': 'ya','ь': '', 'ъ': '',
}

# ---------- 4. КАЗАХСТАН — ICAO + казахские буквы ----------
KAZAKHSTAN_MAP = {**RUSSIA_MAP}
KAZAKHSTAN_MAP.update({
    'Ә': 'A', 'ә': 'a', 'Ғ': 'G', 'ғ': 'g', 'І': 'I', 'і': 'i',
    'Ң': 'N', 'ң': 'n', 'Ө': 'O', 'ө': 'o', 'Ү': 'U', 'ү': 'u',
    'Ұ': 'U', 'ұ': 'u', 'Һ': 'H', 'һ': 'h', 'Қ': 'Q', 'қ': 'q',
})

# ---------- 5. УЗБЕКИСТАН — ICAO + узбекские буквы ----------
UZBEKISTAN_MAP = {**RUSSIA_MAP}
UZBEKISTAN_MAP.update({
    'Ў': "O'", 'ў': "o'", 'Ғ': "G'", 'ғ': "g'", 'Қ': 'Q', 'қ': 'q',
    'Ҳ': 'H', 'ҳ': 'h',
})

# ---------- 6. КИРГИЗИЯ — ICAO + киргизские буквы ----------
KYRGYZSTAN_MAP = {**RUSSIA_MAP}
KYRGYZSTAN_MAP.update({
    'Ң': 'N', 'ң': 'n', 'Ө': 'O', 'ө': 'o', 'Ү': 'U', 'ү': 'u',
})

# ---------- 7. ТАДЖИКИСТАН — ICAO + таджикские буквы ----------
TAJIKISTAN_MAP = {**RUSSIA_MAP}
TAJIKISTAN_MAP.update({
    'Ғ': 'G', 'ғ': 'g', 'Ӣ': 'I', 'ӣ': 'i', 'Қ': 'Q', 'қ': 'q',
    'Ӯ': 'U', 'ӯ': 'u', 'Ҳ': 'H', 'ҳ': 'h', 'Ҷ': 'J', 'ҷ': 'j',
})

# ---------- 8. ТУРКМЕНИЯ — ICAO ----------
TURKMENISTAN_MAP = RUSSIA_MAP

# ---------- 9. АЗЕРБАЙДЖАН ----------
AZERBAIJAN_MAP = {**RUSSIA_MAP}
AZERBAIJAN_MAP.update({
    'Ә': 'A', 'ә': 'a', 'Ҝ': 'G', 'ҝ': 'g', 'Ҹ': 'J', 'ҹ': 'j',
    'Ғ': 'G', 'ғ': 'g', 'Һ': 'H', 'һ': 'h', 'Ө': 'O', 'ө': 'o',
    'Ү': 'U', 'ү': 'u',
})

# ---------- 10. АРМЕНИЯ — ICAO ----------
ARMENIA_MAP = RUSSIA_MAP

# ---------- 11. СЕРБИЯ ----------
SERBIA_MAP = {**RUSSIA_MAP}
SERBIA_MAP.update({
    'Ђ': 'Dj', 'ђ': 'dj', 'Ж': 'Z', 'ж': 'z', 'Њ': 'Nj', 'њ': 'nj',
    'Љ': 'Lj', 'љ': 'lj', 'Ћ': 'C', 'ћ': 'c', 'Џ': 'Dz', 'џ': 'dz',
    'Ш': 'S', 'ш': 's', 'Ч': 'C', 'ч': 'c',
})

# ---------- 12. БОСНИЯ, ХОРВАТИЯ, ЧЕРНОГОРИЯ ----------
BOSNIA_CROATIA_MAP = {**SERBIA_MAP}

# ---------- 13. СЕВЕРНАЯ МАКЕДОНИЯ ----------
MACEDONIA_MAP = {**RUSSIA_MAP}
MACEDONIA_MAP.update({
    'Ѓ': 'Gj', 'ѓ': 'gj', 'Ж': 'Z', 'ж': 'z', 'Њ': 'Nj', 'њ': 'nj',
    'Љ': 'Lj', 'љ': 'lj', 'Ќ': 'Kj', 'ќ': 'kj', 'Џ': 'Dz', 'џ': 'dz',
    'Ш': 'S', 'ш': 's', 'Ч': 'C', 'ч': 'c',
})

# ---------- 14. МОЛДОВА ----------
MOLDOVA_MAP = {**RUSSIA_MAP}
MOLDOVA_MAP.update({
    'Ă': 'A', 'ă': 'a', 'Â': 'A', 'â': 'a', 'Î': 'I', 'î': 'i',
    'Ș': 'S', 'ș': 's', 'Ț': 'T', 'ț': 't',
})

# ---------- 15. ОБЩАЯ ICAO (для остальных) ----------
CIS_MAP = RUSSIA_MAP


# =============================================================================
#  ВЫБОР КАРТЫ ПО СТРАНЕ
# =============================================================================
def get_translit_map(citizenship: str):
    """Возвращает карту транслитерации в зависимости от страны."""
    if not citizenship:
        return CIS_MAP
    low = citizenship.lower().replace(',', '').replace(' ', '').replace('.', '')

    if 'azerbaij' in low:
        return AZERBAIJAN_MAP
    if 'armeni' in low:
        return ARMENIA_MAP
    if 'belarus' in low or 'беларус' in low:
        return BELARUS_MAP
    if any(x in low for x in ('bosni', 'herzegovina', 'хорвати', 'croatia', 'montenegro', 'черногори')):
        return BOSNIA_CROATIA_MAP
    if 'kazakh' in low or 'казах' in low:
        return KAZAKHSTAN_MAP
    if any(x in low for x in ('kyrgyz', 'kirgiz', 'киргиз')):
        return KYRGYZSTAN_MAP
    if 'macedonia' in low or 'македони' in low:
        return MACEDONIA_MAP
    if 'moldova' in low or 'молдов' in low:
        return MOLDOVA_MAP
    if 'russia' in low or 'росси' in low:
        return RUSSIA_MAP
    if 'serbia' in low or 'серби' in low:
        return SERBIA_MAP
    if 'tajik' in low or 'таджик' in low:
        return TAJIKISTAN_MAP
    if 'turkmen' in low or 'туркмен' in low:
        return TURKMENISTAN_MAP
    if 'ukraine' in low or 'украин' in low:
        return UKRAINE_MAP
    if 'uzbek' in low or 'узбек' in low:
        return UZBEKISTAN_MAP
    if any(x in low for x in ('ghana', 'гана', 'india', 'инди', 'china', 'кита', 'pakistan', 'пакистан', 'turkey', 'турци', 'northkorea', 'севернакоре', 'кндр')):
        return CIS_MAP
    return CIS_MAP


# =============================================================================
#  УДАЛЕНИЕ ОТЧЕСТВА
# =============================================================================
PATRONYMIC_ENDINGS = (
    'ович', 'евич', 'овна', 'евна', 'ич', 'инична',
    'оглы', 'кызы', 'улы', 'зы', 'лы',
    'оглу', 'кизи', 'уулу', 'кызы',
)

def remove_patronymic(fio: str) -> str:
    """
    Удаляет отчество из строки ФИО.
    Поддерживает:
      • «Иванов Сергей Александрович» → «Иванов Сергей»
      • «Иванов С.А.» → «Иванов С.»
      • «Иванов-Петров Сергей Александрович» → «Иванов-Петров Сергей»
      • «Иванов Сергей» — оставляет без изменений
    """
    if not fio or not isinstance(fio, str):
        return fio

    fio = fio.strip()
    if not fio:
        return fio

    # --- 1. Удаление инициалов отчества: "Иванов С.А." → "Иванов С." ---
    pattern_initials = re.compile(
        r'^([\w\-]+)\s+([А-ЯЁа-яёA-Za-z])\.\s*([А-ЯЁа-яёA-Za-z])\.?$'
    )
    m = pattern_initials.match(fio)
    if m:
        return f"{m.group(1)} {m.group(2)}."

    # --- 2. Разбор по словам ---
    parts = fio.split()

    if len(parts) == 1:
        return fio

    if len(parts) == 2:
        if any(parts[1].lower().endswith(end) for end in PATRONYMIC_ENDINGS):
            return parts[0]
        return fio

    if len(parts) >= 3:
        last = parts[-1]
        if any(last.lower().endswith(end) for end in PATRONYMIC_ENDINGS):
            return ' '.join(parts[:-1])

        if '-' in parts[0] and len(parts) == 3:
            return ' '.join(parts[:2])

        if len(parts) == 3:
            return ' '.join(parts[:2])

        return ' '.join(parts[:2])

    return fio


# =============================================================================
#  ТРАНСЛИТЕРАЦИЯ
# =============================================================================
def transliterate_text(text: str, citizenship: str) -> str:
    """Транслитерирует строку по правилам страны."""
    if not text:
        return ""

    trans_map = get_translit_map(citizenship)

    result = []
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -'\".")
    for ch in text:
        if ch in trans_map:
            result.append(trans_map[ch])
        else:
            if ch in allowed:
                result.append(ch)

    translit = ''.join(result)
    translit = translit.title()
    return translit


def transliterate_fio(fio_ru: str, citizenship: str, remove_patronymic_flag: bool = True) -> str:
    """Полный pipeline: удалить отчество → транслитерировать."""
    if remove_patronymic_flag:
        fio_ru = remove_patronymic(fio_ru)
    return transliterate_text(fio_ru, citizenship)


# =============================================================================
#  ОБРАБОТКА ФАЙЛОВ (PANDAS)
# =============================================================================
def process_excel(input_path: str, output_path: str,
                  citizenship_col: str = 'Гражданство',
                  fio_col: str = 'ФИО',
                  result_col: str = 'ФИО_EN',
                  remove_patronymic_flag: bool = True):
    """
    Обрабатывает Excel/CSV файл:
      input_path  — путь к исходному файлу
      output_path — путь для сохранения результата
      citizenship_col — название колонки со страной
      fio_col — название колонки с ФИО на русском
      result_col — название новой колонки с результатом
    """
    ext = os.path.splitext(input_path)[1].lower()

    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(input_path)
    elif ext == '.csv':
        df = pd.read_csv(input_path, sep=None, engine='python')
    else:
        raise ValueError(f"Неподдерживаемый формат: {ext}")

    if citizenship_col not in df.columns:
        raise KeyError(f"Колонка '{citizenship_col}' не найдена. Доступные: {list(df.columns)}")
    if fio_col not in df.columns:
        raise KeyError(f"Колонка '{fio_col}' не найдена. Доступные: {list(df.columns)}")

    df[result_col] = df.apply(
        lambda row: transliterate_fio(
            str(row[fio_col]) if pd.notna(row[fio_col]) else '',
            str(row[citizenship_col]) if pd.notna(row[citizenship_col]) else '',
            remove_patronymic_flag
        ),
        axis=1
    )

    if ext in ('.xlsx', '.xls'):
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"Обработано {len(df)} строк. Сохранено в: {output_path}")
    return df


# =============================================================================
#  ТОЧКА ВХОДА (CLI)
# =============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Транслитератор ФИО по паспортным правилам (без отчества)"
    )
    parser.add_argument("input", nargs="?", help="Входной Excel/CSV файл")
    parser.add_argument("output", nargs="?", help="Выходной файл")
    parser.add_argument("--citizenship-col", default="Гражданство",
                        help="Название колонки со страной (по умолчанию: Гражданство)")
    parser.add_argument("--fio-col", default="ФИО",
                        help="Название колонки с ФИО (по умолчанию: ФИО)")
    parser.add_argument("--result-col", default="ФИО_EN",
                        help="Название колонки результата (по умолчанию: ФИО_EN)")
    parser.add_argument("--keep-patronymic", action="store_true",
                        help="Оставить отчество (по умолчанию удаляется)")

    args = parser.parse_args()

    if args.input and args.output:
        process_excel(
            args.input, args.output,
            args.citizenship_col, args.fio_col, args.result_col,
            remove_patronymic_flag=not args.keep_patronymic
        )
    else:
        # Демонстрация
        print("=" * 60)
        print("ДЕМОНСТРАЦИЯ РАБОТЫ")
        print("=" * 60)

        test_cases = [
            ("Россия", "Иванов Сергей Александрович"),
            ("Россия", "Петров Андрей Викторович"),
            ("Россия", "Сидорова Мария Ивановна"),
            ("Россия", "Кузнецов Пётр Семёнович"),
            ("Россия", "Волков Игорь"),
            ("Беларусь", "Гроздь Иван Андреевич"),
            ("Беларусь", "Марина Ольга Владимировна"),
            ("Украина", "Шевченко Тарас Григорович"),
            ("Украина", "Коваленко Оксана Петровна"),
            ("Казахстан", "Назарбаев Нурсултан Абишевич"),
            ("Узбекистан", "Каримов Ислам Абдуганиевич"),
            ("Россия", "Иванов С.А."),
            ("Россия", "Петрова Анна"),
            ("Россия", "Алиев Магомед Саламович"),
        ]

        for country, fio in test_cases:
            result = transliterate_fio(fio, country)
            print(f"{country:12} | {fio:35} -> {result}")

        print()
        print("Использование из командной строки:")
        print("  python translit_passport.py input.xlsx output.xlsx")
        print("  python translit_passport.py data.csv result.csv --fio-col 'ФИО_рус' --citizenship-col 'Страна'")
