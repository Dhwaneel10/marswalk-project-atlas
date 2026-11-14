import os
import shutil

src_dir = r"E:\Python\NASA-Spaceapps\Marswalk\outputs\conference_showcase\joint_mission"
dst_dir = r"C:\Users\dhwan\.gemini\antigravity\brain\0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144\outputs\conference_showcase\joint_mission"

os.makedirs(dst_dir, exist_ok=True)
for fname in os.listdir(src_dir):
    src_f = os.path.join(src_dir, fname)
    dst_f = os.path.join(dst_dir, fname)
    if os.path.isfile(src_f):
        shutil.copy2(src_f, dst_f)
        print(f"Copied {fname} -> artifacts directory.")

print("All showcase screenshots copied to artifacts directory.")
