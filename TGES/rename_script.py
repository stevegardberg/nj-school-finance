import os

# The master folder is the current directory
master_dir = '.' 

# Iterate through every item in the master directory
for folder_name in os.listdir(master_dir):
    folder_path = os.path.join(master_dir, folder_name)
    
    # Check if it's a directory and not a hidden system folder
    if os.path.isdir(folder_path) and not folder_name.startswith('.'):
        print(f"Processing folder: {folder_name}")
        
        # Iterate through files in the subfolder
        for filename in os.listdir(folder_path):
            if filename.endswith(".csv"):
                name, ext = os.path.splitext(filename)
                
                # Check if the folder name (the year) is already in the file
                if folder_name not in name:
                    new_filename = f"{name}_{folder_name}{ext}"
                    old_path = os.path.join(folder_path, filename)
                    new_path = os.path.join(folder_path, new_filename)
                    
                    os.rename(old_path, new_path)
                    print(f"  Renamed: {filename} -> {new_filename}")

print("\nAll files across all folders have been standardized!")