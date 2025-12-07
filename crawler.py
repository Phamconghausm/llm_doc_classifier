# crawler.py
import requests
from bs4 import BeautifulSoup
import os, csv, datetime
from urllib.parse import urljoin
import time

BASE_URL = "https://catalog.data.gov/dataset/?q=pdf&sort=views_recent+desc&ext_location=&ext_bbox=&ext_prev_extent=&res_format=PDF&page="
SAVE_DIR = "data/raw"
LOG_FILE = "data/crawl_log.csv"

os.makedirs(SAVE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

ALLOWED_EXTS = [".pdf", ".docx", ".txt"]

def crawl_files(max_files=10, max_pages=20):
    session = requests.Session()
    session.headers.update(HEADERS)

    crawled = []
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for page in range(1, max_pages + 1):
            url = BASE_URL + str(page)
            print(f"\n===== Crawling page {page}: {url} =====")

            try:
                response = session.get(url, timeout=10)
            except Exception as e:
                print(f"Request error: {e}")
                continue

            if response.status_code != 200:
                print(f"⚠️ HTTP {response.status_code} for page {page}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            dataset_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/dataset/" in href:
                    dataset_links.append(href)

            if not dataset_links:
                print("⚠️ No dataset links found, stop.")
                break

            for dataset in dataset_links:
                if len(crawled) >= max_files:
                    return crawled

                dataset_url = urljoin(url, dataset)
                print(f"→ Enter dataset: {dataset_url}")

                try:
                    r = session.get(dataset_url, timeout=10)
                except Exception:
                    continue

                if r.status_code != 200:
                    continue

                ds_soup = BeautifulSoup(r.text, "html.parser")

                file_links = [
                    a["href"] for a in ds_soup.find_all("a", href=True)
                    if any(a["href"].lower().endswith(ext) for ext in ALLOWED_EXTS)
                ]

                for link in file_links:
                    if len(crawled) >= max_files:
                        return crawled

                    file_url = urljoin(dataset_url, link)
                    file_name = file_url.split("/")[-1]
                    file_path = os.path.join(SAVE_DIR, file_name)

                    if os.path.exists(file_path):
                        continue

                    print(f"⬇️ Downloading: {file_name}")

                    try:
                        file_resp = session.get(file_url, timeout=20)
                    except Exception as e:
                        print(f"Download error: {e}")
                        continue

                    if file_resp.status_code == 403:
                        session.headers["Referer"] = dataset_url
                        time.sleep(1)
                        file_resp = session.get(file_url, timeout=20)

                    if file_resp.status_code != 200:
                        print(f"❌ Cannot download: {file_name} (HTTP {file_resp.status_code})")
                        continue

                    with open(file_path, "wb") as outfile:
                        outfile.write(file_resp.content)

                    writer.writerow([file_name, file_url, datetime.datetime.now().isoformat()])
                    crawled.append(file_name)

                    print(f"✔️ Saved: {file_name}")
                    time.sleep(1.0)

    print(f"\n🎉 Done. Downloaded {len(crawled)} files.")
    return crawled

if __name__ == "__main__":
    crawl_files()