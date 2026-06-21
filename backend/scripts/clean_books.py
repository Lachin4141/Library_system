"""
Cleans books.csv (Book-Crossing dataset from Kaggle) before loading it into the DB.
 
IMPORTANT about this dataset:
- The column delimiter is a semicolon (;), not a comma
- The encoding is latin-1 (ISO-8859-1), not UTF-8
- There are some "broken" rows (extra fields caused by unescaped quotes
  in book titles) — these are skipped while reading
 
Usage:
    python clean_books.py
Expects backend/data/books.csv, creates backend/data/cleaned_books.csv
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
        on_bad_lines="skip",   # skip rows with an incorrect number of fields
        low_memory=False,
    )
    return df
 
 
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAP)
 
    needed = ["isbn", "title", "author", "year", "publisher"]
    df = df[[c for c in needed if c in df.columns]].copy()
 
    # Rows without an ISBN or title are not needed
    df = df.dropna(subset=["isbn", "title"])
 
    # ISBN: strip everything except digits and the letter X (ISBN-10 check digit)
    df["isbn"] = df["isbn"].astype(str).str.strip().str.replace(r"[^0-9Xx]", "", regex=True)
    df = df[df["isbn"].str.len() > 0]
 
    # Remove duplicate ISBNs, keeping the first record
    df = df.drop_duplicates(subset=["isbn"], keep="first")
 
    # Publication year: only a sane range is kept, otherwise left empty
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df.loc[(df["year"] < 1450) | (df["year"] > CURRENT_YEAR), "year"] = pd.NA
    df["year"] = df["year"].astype("Int64")
 
    # Fill missing values in text fields
    df["author"] = df["author"].fillna("Unknown").astype(str).str.strip()
    df["publisher"] = df["publisher"].fillna("Unknown").astype(str).str.strip()
    df["title"] = df["title"].astype(str).str.strip()
 
    return df.reset_index(drop=True)
 
 
def main():
    print(f"Reading {INPUT_FILE} ...")
    raw = load_raw(INPUT_FILE)
    print(f"Rows loaded: {len(raw)}")
 
    cleaned = clean(raw)
    print(f"Rows remaining after cleaning: {len(cleaned)}")
 
    cleaned.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved to {OUTPUT_FILE}")
 
 
if __name__ == "__main__":
    main()