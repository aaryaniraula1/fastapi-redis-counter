\# Web Scraper UI



A React + Vite frontend running in a Docker container and connected to a FastAPI backend.



\## Tech Stack



\* React

\* Vite

\* FastAPI

\* Python

\* Docker

\* Docker Compose



\## Setup and Run



\### 1. Install Backend Dependencies



```bash

python -m pip install -r requirements.txt

```



\### 2. Run FastAPI



FastAPI runs at:



```text

http://127.0.0.1:8000

```



\### 3. Run the Vite Container



Make sure Docker Desktop is running, then open another terminal:



```bash

docker compose up --build

```



Open the frontend at:



```text

http://localhost:5173

```



Click \*\*Check API Connection\*\* to verify the connection with FastAPI.





