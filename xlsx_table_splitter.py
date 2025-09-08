
from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
import numpy as np

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Stringify & strip
    df = df.replace({np.nan: None})
    df.columns = [str(c).strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].apply(lambda x: None if x is None else str(x).strip())
    # Drop rows/cols fully empty (None or empty string)
    df = df.dropna(how="all")
    df = df.loc[:, ~df.isna().all()]
    return df

def _empty_rows_mask(df: pd.DataFrame) -> pd.Series:
    return df.isna().all(axis=1)

def _candidate_header_index(block: pd.DataFrame) -> int:
    # pick the row with the most non-null cells among first few rows
    nn = (~block.isna()).sum(axis=1)
    head_idx = int(nn.iloc[: min(len(block), 6)].idxmax())
    return head_idx

def _split_vertical_blocks(df: pd.DataFrame) -> list[pd.DataFrame]:
    # split on groups of >=1 fully-empty rows
    is_empty = _empty_rows_mask(df)
    if is_empty.all():
        return []
    grp = is_empty.cumsum()
    blocks = []
    for g, sub in df[~is_empty].groupby(grp[~is_empty]):
        sub = _normalize_df(sub)
        if sub.shape[0] and sub.shape[1]:
            blocks.append(sub)
    return blocks

def _split_horizontal_blocks(block: pd.DataFrame) -> list[pd.DataFrame]:
    # Use "sparse" columns (very few non-nulls) as separators
    nonnull_ratio = (~block.isna()).sum(axis=0) / max(1, block.shape[0])
    # Separator: ratio < 0.05
    sep_cols = (nonnull_ratio < 0.05).astype(int)
    # Ensure we always include first and last as borders
    # Build groups of consecutive non-separator columns
    groups = []
    current = []
    for i, col in enumerate(block.columns):
        if sep_cols.iloc[i] == 1:
            if current:
                groups.append(current)
                current = []
        else:
            current.append(col)
    if current:
        groups.append(current)

    if len(groups) <= 1:
        return [block]

    subs = []
    for gcols in groups:
        sub = block[gcols].copy()
        sub = _normalize_df(sub)
        if sub.shape[0] and sub.shape[1]:
            subs.append(sub)
    return subs if subs else [block]

def _to_table(block: pd.DataFrame) -> pd.DataFrame | None:
    if block.empty:
        return None
    # pick header
    hidx = _candidate_header_index(block)
    header = block.iloc[hidx].tolist()
    data = block.iloc[hidx+1:].copy()
    data.columns = header
    # drop columns that are unnamed-like
    data = data.loc[:, [c for c in data.columns if str(c).strip().lower() not in ["", "none", "unnamed: 0", "unnamed: 1"]]]
    # drop rows fully empty
    data = data.replace({"": None, "nan": None}).dropna(how="all")
    if data.shape[1] < 2 or data.shape[0] == 0:
        return None
    return data

def _is_vertical_list(tbl: pd.DataFrame) -> bool:
    return tbl.shape[1] <= 2 and tbl.shape[0] >= 6

def _extract_kv_lines(sheet_name: str, tbl: pd.DataFrame):
    # Treat two-column tables as key/value if second col has values
    kv_records = []
    lines_records = []
    cols = list(tbl.columns)
    if len(cols) == 1:
        # single column: parse "Key: Value"
        for v in tbl[cols[0]].dropna().astype(str):
            s = v.strip()
            if ":" in s:
                k, val = [p.strip() for p in s.split(":", 1)]
                if k and val:
                    kv_records.append({"sheet": sheet_name, "plan": None, "key": k, "value": val})
            else:
                lines_records.append({"sheet": sheet_name, "section": None, "line": s})
    elif len(cols) == 2:
        left, right = cols
        # heuristic: if left looks like label and right like value
        nonnull_right = tbl[right].notna().mean()
        if nonnull_right > 0.4:
            for _, row in tbl.iterrows():
                k = str(row[left]).strip() if pd.notna(row[left]) else None
                v = str(row[right]).strip() if pd.notna(row[right]) else None
                if k and v and k.lower() not in ["", "none"]:
                    kv_records.append({"sheet": sheet_name, "plan": None, "key": k, "value": v})
                elif k:
                    lines_records.append({"sheet": sheet_name, "section": None, "line": k})
        else:
            # treat as lines
            for _, row in tbl.iterrows():
                s = " | ".join([str(x).strip() for x in row.dropna().astype(str).tolist()])
                if s:
                    lines_records.append({"sheet": sheet_name, "section": None, "line": s})
    else:
        # Fallback lines from first column
        for _, row in tbl.iterrows():
            s = " | ".join([str(x).strip() for x in row.dropna().astype(str).tolist()])
            if s:
                lines_records.append({"sheet": sheet_name, "section": None, "line": s})
    return pd.DataFrame(kv_records), pd.DataFrame(lines_records)

def split_excel(path: str | Path, out_dir: str | Path) -> list[str]:
    path = Path(path); out = Path(out_dir); out.mkdir(exist_ok=True, parents=True)
    xls = pd.ExcelFile(path)
    written = []

    for sheet in xls.sheet_names:
        df = xls.parse(sheet_name=sheet, dtype=object)
        df = _normalize_df(df)
        if df.empty:
            continue

        vblocks = _split_vertical_blocks(df)
        if not vblocks:
            vblocks = [df]

        t_idx = 1
        for vb in vblocks:
            hsubs = _split_horizontal_blocks(vb)
            for sub in hsubs:
                tbl = _to_table(sub)
                if tbl is None:
                    continue

                # Save full table
                table_path = out / f"{path.stem.replace(' ','_')}_{sheet.replace(' ','_')}_t{t_idx}.csv"
                tbl.to_csv(table_path, index=False, encoding="utf-8")
                written.append(str(table_path))

                # Additional KV/lines extraction for 1–2 col lists
                if _is_vertical_list(tbl):
                    kv, lines = _extract_kv_lines(sheet, tbl)
                    if not kv.empty:
                        kv_path = out / f"{path.stem.replace(' ','_')}_{sheet.replace(' ','_')}_t{t_idx}_kv.csv"
                        kv.to_csv(kv_path, index=False, encoding="utf-8")
                        written.append(str(kv_path))
                    if not lines.empty:
                        lines_path = out / f"{path.stem.replace(' ','_')}_{sheet.replace(' ','_')}_t{t_idx}_lines.csv"
                        lines.to_csv(lines_path, index=False, encoding="utf-8")
                        written.append(str(lines_path))

                t_idx += 1

    return written

if __name__ == "__main__":
    import sys
    in_path = sys.argv[1] if len(sys.argv) > 1 else None
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "./data"
    if not in_path:
        print("Usage: python xlsx_table_splitter.py <input.xlsx> [out_dir]")
        raise SystemExit(2)
    files = split_excel(in_path, out_dir)
    print(f"Wrote {len(files)} files:")
    for f in files:
        print(" -", f)
