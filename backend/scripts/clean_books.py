"""
Очистка books.csv (Book-Crossing dataset с Kaggle) перед загрузкой в БД.

ВАЖНО про этот датасет:
- Разделитель колонок — точка с запятой (;), а не запятая
- Кодировка — latin-1 (ISO-8859-1), не UTF-8
- Встречаются "битые" строки (лишние поля из-за неэкранированных кавычек
  в названиях книг) — их мы пропускаем при чтении

Запуск:
    python clean_books.py
Ожидает файл backend/data/books.csv, создаёт backend/data/cleaned_books.csv
"""

import pandas as pd

INPUT_FILE = "../data/books.csv"
OUTPUT_FILE = "../data/cleaned_books.csv"
CURRENT_YEAR = 2026

COLUMN_MAP = {
    "ISBN": "isbn",
    "Book-Title": "title",
    "Book-Author": "author",
    "Year-Of-Publication": "year",
    "Publisher": "publisher",
}


def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        quotechar='"',
        on_bad_lines="skip",   # пропускаем строки с некорректным числом полей
        low_memory=False,
    )
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAP)

    needed = ["isbn", "title", "author", "year", "publisher"]
    df = df[[c for c in needed if c in df.columns]].copy()

    # Строки без ISBN или названия нам не нужны
    df = df.dropna(subset=["isbn", "title"])

    # ISBN: убираем всё, кроме цифр и буквы X (контрольная цифра ISBN-10)
    df["isbn"] = df["isbn"].astype(str).str.strip().str.replace(r"[^0-9Xx]", "", regex=True)
    df = df[df["isbn"].str.len() > 0]

    # Удаляем дубликаты ISBN, оставляя первую запись
    df = df.drop_duplicates(subset=["isbn"], keep="first")

    # Год публикации: только разумный диапазон, иначе оставляем пустым
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df.loc[(df["year"] < 1450) | (df["year"] > CURRENT_YEAR), "year"] = pd.NA
    df["year"] = df["year"].astype("Int64")

    # Заполняем пропуски в текстовых полях
    df["author"] = df["author"].fillna("Unknown").astype(str).str.strip()
    df["publisher"] = df["publisher"].fillna("Unknown").astype(str).str.strip()
    df["title"] = df["title"].astype(str).str.strip()

    return df.reset_index(drop=True)


def main():
    print(f"Читаю {INPUT_FILE} ...")
    raw = load_raw(INPUT_FILE)
    print(f"Загружено строк: {len(raw)}")

    cleaned = clean(raw)
    print(f"После очистки осталось строк: {len(cleaned)}")

    cleaned.to_csv(OUTPUT_FILE, index=False)
    print(f"Сохранено в {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
