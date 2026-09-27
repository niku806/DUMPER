import json
import os
import glob

# Current folder me saari JSON files
files = glob.glob("*.json")
print(f"📁 Total files: {len(files)}")

if not files:
    print("❌ Koi JSON file nahi mili. Folder check kar!")
    exit()

def esc(s):
    """SQL safe escape"""
    if s is None:
        return ""
    return str(s).replace("'", "''").replace("\n", " ").replace("\r", " ").strip()

def json_arr_to_str(arr):
    """Array ko comma-separated string banao"""
    if isinstance(arr, list):
        return esc(",".join(str(x) for x in arr))
    return esc(arr)

chunk_num = 0
chunk_size = 2000
counter = 0
out = None

def open_new_chunk():
    global out, chunk_num
    if out:
        out.write("COMMIT;\n")
        out.close()
    filename = f"chunk_{chunk_num}.sql"
    out = open(filename, "w", encoding="utf-8")
    out.write("BEGIN TRANSACTION;\n")
    print(f"📝 Writing {filename}...")
    chunk_num += 1

open_new_chunk()

success = 0
failed = 0

for i, file in enumerate(files, 1):
    try:
        with open(file, "r", encoding="utf-8") as f:
            d = json.load(f)
        
        anime_id = file.replace(".json", "")
        title = esc(d.get("title", ""))
        poster = esc(d.get("image", ""))
        
        # year string ko int me convert
        year_raw = d.get("year", 0)
        try:
            year = int(str(year_raw).strip()[:4]) if year_raw else 0
        except:
            year = 0
        
        genres = json_arr_to_str(d.get("genres", []))
        synopsis = esc(d.get("description", ""))[:800]
        total_eps = int(d.get("total_episodes", 0) or 0)
        
        # Agar total_episodes na ho toh episodes_data se count karo
        if total_eps == 0:
            eps_data = d.get("episodes_data", d.get("episodes", []))
            total_eps = len(eps_data)
        
        sql = (
            f"INSERT OR REPLACE INTO anime "
            f"(id,title,poster,year,genres,synopsis,total_episodes) VALUES "
            f"('{esc(anime_id)}','{title}','{poster}',{year},"
            f"'{genres}','{synopsis}',{total_eps});\n"
        )
        
        out.write(sql)
        counter += 1
        success += 1
        
        # Chunk limit cross
        if counter >= chunk_size:
            counter = 0
            open_new_chunk()
        
        if i % 1000 == 0:
            print(f"✅ Processed: {i}/{len(files)}")
    
    except Exception as e:
        failed += 1
        print(f"⚠️ Skip {file}: {e}")

# Last chunk close
if out:
    out.write("COMMIT;\n")
    out.close()

print(f"\n🎉 Done!")
print(f"✅ Success: {success}")
print(f"❌ Failed: {failed}")
print(f"📦 Total chunks: {chunk_num}")
