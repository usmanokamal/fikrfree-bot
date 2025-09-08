import pandas as pd
import os

# === Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "raw", "FikrFree_Data.xlsx")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "Fikrfree_Cleaned_Data.csv")

# === Step 1: Load sheet ===
df = pd.read_excel(INPUT_FILE, sheet_name="AI Chat Bot", header=2)

# === Step 2: Rename columns ===
df.columns = [
    "ProductOwner",
    "ProductName",
    "ProductID",
    "ProductDescription",
    "Variant",
    "PrepaidDaily",
    "PostpaidMonthly",
    "MonthlyPrice",
    "YearlyPrice",
    "Benefit1",
    "Description1",
    "Benefit2",
    "Description2",
    "Benefit3",
    "Description3",
    "Benefit4",
    "Description4",
    "Benefit5",
    "Description5",
    "DocumentsRequired",
]

# === Step 3: Forward fill product info ===
df[["ProductOwner", "ProductName", "ProductID", "ProductDescription"]] = df[
    ["ProductOwner", "ProductName", "ProductID", "ProductDescription"]
].ffill()

# === Step 4: Keep only rows with actual variants (case-insensitive, includes Ace) ===
variant_pattern = r"\b(Bronze|Silver|Gold|Platinum|Diamond|Crown|Default|Ace)\b"
mask = df["Variant"].astype(str).str.contains(variant_pattern, case=False, na=False)
clean_df = df[mask].copy()

# === Step 5: Clean text fields ===
clean_df = clean_df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
clean_df = clean_df.dropna(how="all")

# === Step 6: Save final CSV ===
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
clean_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

# Quick summary by Variant (for verification)
try:
    variant_counts = (
        clean_df["Variant"].astype(str).str.strip().str.title().value_counts()
    )
    print("Variant counts in cleaned data:")
    for v, c in variant_counts.items():
        print(f"  - {v}: {c}")
except Exception:
    pass

print(f"✅ Cleaned dataset saved at: {OUTPUT_FILE}")
