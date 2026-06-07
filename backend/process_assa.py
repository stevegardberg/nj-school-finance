import pandas as pd
import uuid

# Load your processed data
df = pd.read_csv('/Users/steve/nj-school-finance/enrollment_ready_for_supabase.csv')

# 1. Map to your exact table columns
df = df.rename(columns={'cds': 'cds_code', 'fiscal_year': 'fiscal_year', 'student_count': 'student_count'})

# 2. Add the missing columns required by the table
df['uid'] = [str(uuid.uuid4()) for _ in range(len(df))] # Generate unique IDs
df['district_id'] = df['cds_code'].str[-4:]             # Extract ID from CDS
df['district_name'] = 'Unknown'                         # Placeholder
df['grade_level'] = 'Total'                             # Placeholder

# 3. Reorder to match your table schema exactly
final_df = df[['uid', 'cds_code', 'fiscal_year', 'district_id', 'district_name', 'grade_level', 'student_count']]

# 4. Export
final_df.to_csv('/Users/steve/nj-school-finance/final_supabase_import.csv', index=False)
print("File 'final_supabase_import.csv' created with all 7 required columns.")