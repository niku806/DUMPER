import json, glob, os

index = []
files = glob.glob("*.json")
files = [f for f in files if "masterjson" not in f.lower() and "index" not in f.lower()]

for i, file in enumerate(files, 1):
    try:
        with open(file, "r", encoding="utf-8") as f:
            d = json.load(f)

        slug = file.replace(".json", "")
        title = d.get("title", "").strip()
        if not title:
            continue

        eps_data = d.get("episodes_data", d.get("episodes", []))
        total_eps = d.get("total_episodes", len(eps_data))
        try: total_eps = int(total_eps)
        except: total_eps = len(eps_data)

        yr = d.get("year", "")
        try: yr = int(str(yr).strip()[:4]) if yr else 0
        except: yr = 0

        index.append({
            "id": slug,
            "title": title,
            "poster": d.get("image", ""),
            "year": yr,
            "genres": d.get("genres", []),
            "total_episodes": total_eps,
            "synopsis": (d.get("description", "") or "")[:300],
        })

        if i % 100 == 0:
            print(f"  {i}/{len(files)}")
    except Exception as e:
        print(f"Skip {file}: {e}")

with open("index.json", "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

size = os.path.getsize("index.json") / 1024
print(f"\n✅ index.json ready! {len(index)} entries, {size:.1f} KB")