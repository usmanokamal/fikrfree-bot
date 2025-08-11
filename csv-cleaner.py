import os
import pandas as pd
from bs4 import BeautifulSoup

# Directories
input_dir = './Raw'
output_dir = './data'  # <-- changed from ./app/data
os.makedirs(output_dir, exist_ok=True)

columns_to_remove = [
    'createddate','createdby','url','machine_name','modifiedby','modifieddate','files',
    'videos','expiredfrom','emails','c_escalation','created_by','created_date','createby',
    'modify_by','modify_date','displayin','fsehandling','level3poc','ovideos',
    'create_by','create_date'
]

def clean_html(text):
    return BeautifulSoup(str(text), "html.parser").get_text(separator=" ", strip=True)

def load_csv_with_fallback(path):
    """Try multiple encodings until one works."""
    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Could not read {path} with common encodings.")

def clean_csv(file_path):
    df = load_csv_with_fallback(file_path)
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.loc[:, ~df.columns.str.contains('^unnamed', case=False)]
    df.drop(columns=[c for c in columns_to_remove if c in df.columns], inplace=True, errors='ignore')

    def is_garbage(col):
        col_str = col.astype(str).str.strip().str.lower()
        return col_str.isin(['', 'nan']).all()
    df = df.loc[:, ~df.apply(is_garbage)]

    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(clean_html)

    return df

# Process all CSVs
for filename in os.listdir(input_dir):
    if filename.lower().endswith('.csv'):
        inp = os.path.join(input_dir, filename)
        try:
            cleaned = clean_csv(inp)
            out = os.path.join(output_dir, f"cleaned_{filename}")
            cleaned.to_csv(out, index=False, encoding='utf-8')
            print(f"✅ Saved: {out}")
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
