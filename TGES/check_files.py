# Create a small script or add this to your existing one
import pandas as pd

skipped_files = [
    'October 2020 DRTRS_2021.xlsx',
    'DETAIL_FY15_MAY18_2017.XLSX',
    'DETAIL_FY16_MAY18_2017.XLSX',
    'DETAIL_FY15_JUL21_2016.XLSX',
    'DETAIL_FY14_JUL21_2016.XLSX',
    'October 2021 DRTRS_2022.xlsx',
    'October 2022 DRTRS_2023.xlsx'
]

for f in skipped_files:
    try:
        # Load the file to inspect headers
        df = pd.read_excel(f, header=2) # Adjust header if needed
        print(f"File: {f} | Columns: {list(df.columns)}")
    except:
        print(f"Could not read {f}")