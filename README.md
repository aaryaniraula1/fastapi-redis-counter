# Forest Government Crawler

A prototype for discovering official Nepal forest-government websites and identifying their organizational hierarchy.

It uses Scrapy for crawling and Gemini API for extracting organization names and direct parent relationships from website header/branding evidence.

## Run Crawler

```bash
docker compose up --build
```

## Run Hierarchy Extraction

```bash
python gemini_hierarchy.py
```

Hierarchy results are saved to `output/final_hierarchy.json`.