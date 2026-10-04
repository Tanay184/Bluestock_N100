import pandas as pd, glob, os
for folder, hdr in (("data/raw", 1), ("data/supporting", 0)):
    for f in sorted(glob.glob(f"{folder}/*.xlsx")):
        for sh, df in pd.read_excel(f, header=hdr, sheet_name=None).items():
            print("=" * 60, f"\n{os.path.basename(f)} [{sh}] {df.shape}")
            print(list(df.columns)); print(df.head(2).to_string())