# KleinanzeigenAssistent

KleinanzeigenAssistent is an interface for [kleinanzeigen-bot](https://github.com/Second-Hand-Friends/kleinanzeigen-bot) that includes AI integration for creating the ads.

By default, we make use of Google's free API but this can easily be changed by editing `app/design_listing.py`.

## Features
- Automatically split image dump by items (black image = separator)
- Select and crop images quickly in the web interface
- Give information on the item via voice interface
- LLM populates the ad title, description, etc.
- kleinanzeigen-bot publishes the ads 

## Setup Instructions

### 1. Install kleinanzeigen-bot and chromium
- [kleinanzeigen-bot](https://github.com/Second-Hand-Friends/kleinanzeigen-bot/releases/tag/latest)
- [chromium](https://www.chromium.org/getting-involved/download-chromium/)

### 2. Clone the Repository
```bash
git clone https://github.com/wobbba/KleinanzeigenAssistent
cd KleinanzeigenAssistent
```

### 3. Create and Activate a Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Prepare Configuration Files
```bash
cp config.yaml.template config.yaml
cp kleinanzeigen_config.yaml.template kleinanzeigen_config.yaml
```
- Edit the following fields in `config.yaml`:
  - `klein_bin`: Path to your kleinanzeigen-bot executable
  - `chromium_path`: Path to your Chromium executable
  - `google_api_key`: Your Google API key for access to Gemini (get one from [Google AI Studio](https://aistudio.google.com/app/apikey))
  - If you wish to access the interface from another device in your network, change `host` to `0.0.0.0` and access via your device's local IP and the given port.
- Edit the following fields in `kleinanzeigen_config.yaml`:
  - `browser.user_data_dir` / `browser.arguments.user_data_dir`: Path to your Chromium profiles directory (they need to match)
  - `login.username` and `login.password`: Your Kleinanzeigen credentials

### 6. Prepare Chromium
To avoid issues with cookie popups, open Chromium and log into Kleinanzeigen, ensuring that cookie preferences are saved.

## Usage

1. Take photos of the items you want to sell. Take one black image between each item (cover camera lens). This tells the assistent that a new item starts. 

2. Place images in the `inbox/` directory.
3. Start the server:
   ```bash
   source venv/bin/activate
   python -m app.main
   ```
4. The web UI will open automatically at `http://127.0.0.1:8000/`.
5. For each image, select the image regions you desire, click `Record`, and talk about relevant details for the ad, then click `Stop`. Alternatively, you can also fill out the form by hand.
6. Verify the form values are acceptable.
7. Click `Submit & Next`. Repeat for all items.
8. Click `Pending` and `Publish All Now`.
9. Let kleinanzeigen-bot publish your ads.

## Configuration Overview
- `config.yaml`: Config for this project
- `kleinanzeigen_config.yaml`: Config for kleinanzeigen-bot
- `categories.txt`: Contains the category IDs from which the LLM chooses. A shortened and condensed version of [this file](https://github.com/Second-Hand-Friends/kleinanzeigen-bot/blob/main/src/kleinanzeigen_bot/resources/categories.yaml).

See template files.
