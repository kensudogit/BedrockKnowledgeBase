import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8180"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=True)
