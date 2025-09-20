import os, glob

# Step 1: List all JSON files
json_files = glob.glob("**/*.json", recursive=True)
print("Found JSON files:")
for f in json_files:
    print(f)

# Step 2: Confirm deletion
confirm = input("Do you want to delete all these JSON files? (yes/no): ")
if confirm.lower() == "yes":
    for f in json_files:
        os.remove(f)
    print(f"✅ Deleted {len(json_files)} JSON files.")
else:
    print("❌ Deletion canceled.")
