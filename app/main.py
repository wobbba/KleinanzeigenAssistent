import threading
import time
import webbrowser
import uvicorn

from app.common import HOST, PORT
from app.server import server
from app.input import process_inbox


if __name__ == "__main__":
    
    process_inbox()

    url = f"http://{HOST}:{PORT}/"


    # Open the browser in a separate thread after a delay (uvicorn.run is blocking)
    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(server, host=HOST, port=PORT, log_level="info")
