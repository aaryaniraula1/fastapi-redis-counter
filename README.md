# Forest Government Crawler

A Scrapy based prototype that crawls official Nepal forest-government 
websites , finds pages related 
to organizational structure, acts, reports, and similar topics, and 
saves them as structured JSON.

## Run it
docker compose up --build

Output is saved to output/forest_data.json (stops automatically after 
200 relevant pages found).