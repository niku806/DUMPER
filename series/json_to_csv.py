import os
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.expanduser(
    "~/storage/downloads/scrap/data/series"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "anime_dataset.csv"
)

# Exactly 8 threads as requested
THREADS = 8

# ============================================================
# HELPERS
# ============================================================

def clean(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.replace("\r", " ").replace("\n", " ").strip()

    return str(value)


def json_text(value):
    if value is None:
        return ""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":")
    )


def list_text(value):
    if not isinstance(value, list):
        return clean(value)

    return " | ".join(
        clean(x) for x in value
    )


def get_slug(url):
    if not url:
        return ""

    try:
        path = urlparse(url).path.strip("/")

        if not path:
            return ""

        return path.split("/")[-1]

    except Exception:
        return ""


def get_video_id(url):
    if not url:
        return ""

    try:
        query = parse_qs(
            urlparse(url).query
        )

        values = query.get("trid")

        if values:
            return clean(values[0])

    except Exception:
        pass

    return ""


# ============================================================
# FIND JSON FILES
# ============================================================

def find_json_files():

    files = []

    for root, dirs, filenames in os.walk(BASE_DIR):

        for filename in filenames:

            if not filename.lower().endswith(".json"):
                continue

            path = os.path.join(
                root,
                filename
            )

            if os.path.abspath(path) == os.path.abspath(
                OUTPUT_FILE
            ):
                continue

            files.append(path)

    return sorted(files)


# ============================================================
# LOAD ONE JSON
# ============================================================

def load_json(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, dict):

            return {
                "path": path,
                "data": None,
                "error": "JSON root is not an object"
            }

        return {
            "path": path,
            "data": data,
            "error": ""
        }

    except Exception as e:

        return {
            "path": path,
            "data": None,
            "error": str(e)
        }


# ============================================================
# GET EPISODES
# ============================================================

def get_episodes(series):

    episodes_data = series.get(
        "episodes_data"
    )

    if isinstance(episodes_data, list):

        return [
            x for x in episodes_data
            if isinstance(x, dict)
        ]

    episodes = series.get(
        "episodes"
    )

    if isinstance(episodes, list):

        return [
            x for x in episodes
            if isinstance(x, dict)
        ]

    # Keep series even if it has no episode list
    return [{}]


# ============================================================
# ANALYZE ONE FILE
# ============================================================

def analyze(result):

    data = result.get("data")

    if not isinstance(data, dict):

        return {
            "streams": 0,
            "downloads": 0,
            "episodes": 0
        }

    max_streams = 0
    max_downloads = 0

    episodes = get_episodes(data)

    for episode in episodes:

        streams = episode.get(
            "streaming_servers",
            []
        )

        downloads = episode.get(
            "download_links",
            []
        )

        if isinstance(streams, list):

            max_streams = max(
                max_streams,
                len(streams)
            )

        if isinstance(downloads, list):

            max_downloads = max(
                max_downloads,
                len(downloads)
            )

    return {
        "streams": max_streams,
        "downloads": max_downloads,
        "episodes": len(episodes)
    }


# ============================================================
# CREATE HEADERS
# ============================================================

def create_headers(
    max_streams,
    max_downloads
):

    headers = [
        "ID",
        "ANIME",
        "SLUG",
        "SEASON",
        "EPISODE",
        "TITLE",
        "VIDEO_ID",
        "VIDEO_URL",
        "DOWNLOAD_URL",
        "BANNER_URL",
        "POSTER_URL",
        "THUMBNAIL_URL",
        "CATEGORY 1",
        "CATEGORY 2",
        "CATEGORY 3",
        "DATE",
        "KEYWORDS",
    ]

    # --------------------------------------------------------
    # STREAMING COLUMNS
    # --------------------------------------------------------

    for number in range(
        1,
        max_streams + 1
    ):

        suffix = (
            ""
            if number == 1
            else str(number)
        )

        headers.extend([
            f"VIDEO_URL{suffix}",
            f"VIDEO_NAME{suffix}",
            f"VIDEO_RAW{suffix}",
        ])

    # --------------------------------------------------------
    # DOWNLOAD COLUMNS
    # --------------------------------------------------------

    for number in range(
        1,
        max_downloads + 1
    ):

        suffix = (
            ""
            if number == 1
            else str(number)
        )

        headers.extend([
            f"DOWNLOAD_URL{suffix}",
            f"DOWNLOAD_LABEL{suffix}",
            f"DOWNLOAD_DECODED{suffix}",
        ])

    # --------------------------------------------------------
    # EPISODE DATA
    # --------------------------------------------------------

    headers.extend([
        "DESCRIPTION",
        "YEAR",
        "DURATION",
        "RATING",
        "GENRES",
        "CAST",
        "NEXT_EPISODE",
        "PREV_EPISODE",
        "IFRAMES",
        "EPISODE_IMAGE",
    ])

    # --------------------------------------------------------
    # SERIES DATA
    # --------------------------------------------------------

    headers.extend([
        "SERIES_URL",
        "SERIES_DESCRIPTION",
        "SERIES_YEAR",
        "SERIES_GENRES",
        "SERIES_CAST",
        "SERIES_IMAGE",
        "SOURCE_JSON_FILE",
        "RAW_JSON",
    ])

    return headers


# ============================================================
# KEYWORDS
# ============================================================

def make_keywords(
    series,
    episode
):

    values = []

    title = series.get("title")

    if title:
        values.append(
            clean(title)
        )

    episode_title = episode.get(
        "title"
    )

    if episode_title:
        values.append(
            clean(episode_title)
        )

    genres = (
        episode.get("genres")
        or series.get("genres")
        or []
    )

    if isinstance(genres, list):

        values.extend(
            clean(x)
            for x in genres
        )

    cast = (
        episode.get("cast")
        or series.get("cast")
        or []
    )

    if isinstance(cast, list):

        values.extend(
            clean(x)
            for x in cast
        )

    year = (
        episode.get("year")
        or series.get("year")
    )

    if year:
        values.append(
            clean(year)
        )

    # Remove duplicate keywords
    output = []
    seen = set()

    for value in values:

        value = clean(value)

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

    return " | ".join(output)


# ============================================================
# CREATE ONE ROW
# ============================================================

def make_row(
    series,
    episode,
    source_file,
    row_id,
    max_streams,
    max_downloads
):

    row = {}

    # --------------------------------------------------------
    # BASIC SERIES DATA
    # --------------------------------------------------------

    anime = clean(
        series.get("title")
    )

    series_url = clean(
        series.get("url")
    )

    slug = get_slug(
        series_url
    )

    series_image = clean(
        series.get("image")
    )

    series_genres = series.get(
        "genres",
        []
    )

    series_cast = series.get(
        "cast",
        []
    )

    # --------------------------------------------------------
    # EPISODE DATA
    # --------------------------------------------------------

    episode_url = clean(
        episode.get("url")
    )

    season = clean(
        episode.get("season")
    )

    episode_number = clean(
        episode.get("episode")
    )

    episode_title = clean(
        episode.get("title")
    )

    # --------------------------------------------------------
    # STREAMS
    # --------------------------------------------------------

    streams = episode.get(
        "streaming_servers",
        []
    )

    if not isinstance(streams, list):
        streams = []

    # --------------------------------------------------------
    # DOWNLOADS
    # --------------------------------------------------------

    downloads = episode.get(
        "download_links",
        []
    )

    if not isinstance(downloads, list):
        downloads = []

    # --------------------------------------------------------
    # VIDEO ID
    # --------------------------------------------------------

    video_id = ""

    for stream in streams:

        if not isinstance(stream, dict):
            continue

        stream_url = clean(
            stream.get("url")
        )

        video_id = get_video_id(
            stream_url
        )

        if video_id:
            break

    if not video_id:

        video_id = get_video_id(
            episode_url
        )

    # --------------------------------------------------------
    # BASE COLUMNS
    # --------------------------------------------------------

    row["ID"] = row_id

    row["ANIME"] = anime

    row["SLUG"] = slug

    row["SEASON"] = season

    row["EPISODE"] = episode_number

    row["TITLE"] = episode_title

    row["VIDEO_ID"] = video_id

    # First URL columns
    row["VIDEO_URL"] = (
        clean(streams[0].get("url"))
        if streams
        and isinstance(streams[0], dict)
        else ""
    )

    row["DOWNLOAD_URL"] = (
        clean(downloads[0].get("url"))
        if downloads
        and isinstance(downloads[0], dict)
        else ""
    )

    row["BANNER_URL"] = series_image

    row["POSTER_URL"] = clean(
        episode.get("image")
        or series_image
    )

    row["THUMBNAIL_URL"] = clean(
        episode.get("image")
    )

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    for i in range(3):

        key = f"CATEGORY {i + 1}"

        if (
            isinstance(series_genres, list)
            and i < len(series_genres)
        ):

            row[key] = clean(
                series_genres[i]
            )

        else:

            row[key] = ""

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    row["DATE"] = clean(
        episode.get("year")
        or series.get("year")
    )

    # --------------------------------------------------------
    # KEYWORDS
    # --------------------------------------------------------

    row["KEYWORDS"] = make_keywords(
        series,
        episode
    )

    # --------------------------------------------------------
    # ALL STREAMS
    # --------------------------------------------------------

    for i in range(max_streams):

        number = i + 1

        suffix = (
            ""
            if number == 1
            else str(number)
        )

        url_key = f"VIDEO_URL{suffix}"
        name_key = f"VIDEO_NAME{suffix}"
        raw_key = f"VIDEO_RAW{suffix}"

        if i < len(streams):

            stream = streams[i]

            if isinstance(stream, dict):

                row[url_key] = clean(
                    stream.get("url")
                )

                row[name_key] = clean(
                    stream.get("name")
                )

                row[raw_key] = clean(
                    stream.get("raw")
                )

            else:

                row[url_key] = clean(
                    stream
                )

                row[name_key] = ""
                row[raw_key] = ""

        else:

            row[url_key] = ""
            row[name_key] = ""
            row[raw_key] = ""

    # --------------------------------------------------------
    # ALL DOWNLOADS
    # --------------------------------------------------------

    for i in range(max_downloads):

        number = i + 1

        suffix = (
            ""
            if number == 1
            else str(number)
        )

        url_key = (
            f"DOWNLOAD_URL{suffix}"
        )

        label_key = (
            f"DOWNLOAD_LABEL{suffix}"
        )

        decoded_key = (
            f"DOWNLOAD_DECODED{suffix}"
        )

        if i < len(downloads):

            download = downloads[i]

            if isinstance(download, dict):

                row[url_key] = clean(
                    download.get("url")
                )

                row[label_key] = clean(
                    download.get("label")
                )

                row[decoded_key] = clean(
                    download.get("decoded")
                )

            else:

                row[url_key] = clean(
                    download
                )

                row[label_key] = ""
                row[decoded_key] = ""

        else:

            row[url_key] = ""
            row[label_key] = ""
            row[decoded_key] = ""

    # --------------------------------------------------------
    # EPISODE EXTRA
    # --------------------------------------------------------

    row["DESCRIPTION"] = clean(
        episode.get("description")
    )

    row["YEAR"] = clean(
        episode.get("year")
        or series.get("year")
    )

    row["DURATION"] = clean(
        episode.get("duration")
    )

    row["RATING"] = clean(
        episode.get("rating")
    )

    row["GENRES"] = list_text(
        episode.get("genres")
        or series_genres
    )

    row["CAST"] = list_text(
        episode.get("cast")
        or series_cast
    )

    row["NEXT_EPISODE"] = clean(
        episode.get("next_episode")
    )

    row["PREV_EPISODE"] = clean(
        episode.get("prev_episode")
    )

    row["IFRAMES"] = json_text(
        episode.get(
            "iframes",
            []
        )
    )

    row["EPISODE_IMAGE"] = clean(
        episode.get("image")
    )

    # --------------------------------------------------------
    # SERIES EXTRA
    # --------------------------------------------------------

    row["SERIES_URL"] = series_url

    row["SERIES_DESCRIPTION"] = clean(
        series.get("description")
    )

    row["SERIES_YEAR"] = clean(
        series.get("year")
    )

    row["SERIES_GENRES"] = list_text(
        series_genres
    )

    row["SERIES_CAST"] = list_text(
        series_cast
    )

    row["SERIES_IMAGE"] = series_image

    row["SOURCE_JSON_FILE"] = os.path.basename(
        source_file
    )

    # --------------------------------------------------------
    # COMPLETE ORIGINAL DATA
    # --------------------------------------------------------

    row["RAW_JSON"] = json_text({
        "series": series,
        "episode": episode
    })

    return row


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("              ANIME JSON -> CSV")
    print("=" * 70)
    print()

    if not os.path.isdir(BASE_DIR):

        print("ERROR: Folder not found:")
        print(BASE_DIR)
        print()
        print(
            "Check that the folder is:"
        )
        print(
            "~/storage/downloads/scrap/data/series"
        )

        return

    # --------------------------------------------------------
    # FIND FILES
    # --------------------------------------------------------

    print("Searching JSON files...")

    files = find_json_files()

    print(
        f"JSON files found: {len(files)}"
    )

    if not files:
        print()
        print("No JSON files found.")
        return

    # --------------------------------------------------------
    # FIRST PASS
    # 8 THREADS
    # --------------------------------------------------------

    print()
    print(
        f"Loading/analyzing with {THREADS} threads..."
    )

    max_streams = 0
    max_downloads = 0
    total_episodes = 0

    valid_files = []
    errors = []

    # Keep only a small batch in memory.
    # This prevents the phone from loading
    # thousands of JSON files at once.
    BATCH_SIZE = THREADS * 2

    for batch_start in range(
        0,
        len(files),
        BATCH_SIZE
    ):

        batch = files[
            batch_start:
            batch_start + BATCH_SIZE
        ]

        with ThreadPoolExecutor(
            max_workers=THREADS
        ) as executor:

            future_map = {
                executor.submit(
                    load_json,
                    path
                ): path
                for path in batch
            }

            for future in as_completed(
                future_map
            ):

                result = future.result()

                if result["data"] is None:

                    errors.append(
                        result
                    )

                    continue

                stats = analyze(
                    result
                )

                max_streams = max(
                    max_streams,
                    stats["streams"]
                )

                max_downloads = max(
                    max_downloads,
                    stats["downloads"]
                )

                total_episodes += stats[
                    "episodes"
                ]

                valid_files.append(
                    result
                )

        done = min(
            batch_start + BATCH_SIZE,
            len(files)
        )

        print(
            f"\rAnalyzed: {done}/{len(files)}"
            f" | Streams max: {max_streams}"
            f" | Downloads max: {max_downloads}",
            end="",
            flush=True
        )

    print()
    print()

    print(
        f"Valid JSON files : {len(valid_files)}"
    )

    print(
        f"Failed JSON files: {len(errors)}"
    )

    print(
        f"Total episodes   : {total_episodes}"
    )

    print()
    print(
        f"MAX STREAMS      : {max_streams}"
    )

    print(
        f"MAX DOWNLOADS    : {max_downloads}"
    )

    # --------------------------------------------------------
    # HEADERS
    # --------------------------------------------------------

    headers = create_headers(
        max_streams,
        max_downloads
    )

    print()
    print(
        f"CSV columns      : {len(headers)}"
    )

    # --------------------------------------------------------
    # WRITE CSV
    # --------------------------------------------------------

    print()
    print("Creating CSV...")
    print()

    row_id = 1
    total_rows = 0

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=headers,
            extrasaction="ignore"
        )

        # HEADER FIRST
        writer.writeheader()

        # Process JSON files in batches again.
        # This keeps memory under control.
        for file_index in range(
            0,
            len(valid_files),
            BATCH_SIZE
        ):

            batch = valid_files[
                file_index:
                file_index + BATCH_SIZE
            ]

            for result in batch:

                series = result["data"]

                episodes = get_episodes(
                    series
                )

                for episode in episodes:

                    row = make_row(
                        series=series,
                        episode=episode,
                        source_file=result["path"],
                        row_id=row_id,
                        max_streams=max_streams,
                        max_downloads=max_downloads
                    )

                    writer.writerow({
                        header: row.get(
                            header,
                            ""
                        )
                        for header in headers
                    })

                    row_id += 1
                    total_rows += 1

                # Flush after every file
                csv_file.flush()

            processed_files = min(
                file_index + BATCH_SIZE,
                len(valid_files)
            )

            print(
                f"\rCSV: "
                f"{processed_files}/{len(valid_files)} files"
                f" | Rows: {total_rows}",
                end="",
                flush=True
            )

    print()
    print()

    # --------------------------------------------------------
    # VERIFY OUTPUT
    # --------------------------------------------------------

    if os.path.exists(
        OUTPUT_FILE
    ):

        size = os.path.getsize(
            OUTPUT_FILE
        )

        size_mb = (
            size /
            (1024 * 1024)
        )

    else:

        size_mb = 0

    print("=" * 70)
    print("                       DONE")
    print("=" * 70)
    print()

    print(
        f"JSON files processed : {len(valid_files)}"
    )

    print(
        f"JSON files failed    : {len(errors)}"
    )

    print(
        f"CSV rows             : {total_rows}"
    )

    print(
        f"CSV columns          : {len(headers)}"
    )

    print(
        f"Max streams          : {max_streams}"
    )

    print(
        f"Max downloads        : {max_downloads}"
    )

    print(
        f"CSV size             : {size_mb:.2f} MB"
    )

    print()
    print("OUTPUT:")
    print(OUTPUT_FILE)

    # --------------------------------------------------------
    # ERROR REPORT
    # --------------------------------------------------------

    if errors:

        error_file = os.path.join(
            BASE_DIR,
            "csv_conversion_errors.txt"
        )

        with open(
            error_file,
            "w",
            encoding="utf-8"
        ) as f:

            for error in errors:

                f.write(
                    error["path"]
                )

                f.write("\n")

                f.write(
                    error["error"]
                )

                f.write(
                    "\n\n"
                )

        print()
        print(
            "Some JSON files failed."
        )

        print(
            "Error report:"
        )

        print(
            error_file
        )

    print()
    print("Finished.")


if __name__ == "__main__":
    main()