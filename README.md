# Listonic (Home Assistant Custom Integration)

Sync and manage your **Listonic shopping lists** directly in Home Assistant.  
This custom integration connects to **Listonic Cloud** via Google OAuth2, retrieves your shopping lists, and exposes them as **To-Do lists** in HA.

[![Validate with HACS](https://img.shields.io/badge/HACS-validated-41BDF5)](https://hacs.xyz/)  
[![hassfest](https://img.shields.io/badge/hassfest-passing-brightgreen)](https://developers.home-assistant.io/docs/creating_integration_manifest/)  
[![MIT License](https://img.shields.io/badge/license-MIT-informational)](LICENSE.md)

> ⚠️ This is a third-party project, not affiliated with Listonic.

---

## ✨ Features

- Login with your **Google account** via OAuth2 (secure flow).  
- Automatic discovery of all your **Listonic shopping lists**.  
- Each Listonic list is represented as a **To-Do list entity** in Home Assistant.  
- Full **two-way sync** between Listonic mobile app and Home Assistant:
  - Add / delete / rename lists  
  - Add / delete / update items  
  - Check / uncheck items  
- Supports **sharing lists** in Listonic app (with family/friends using different Google accounts) — changes are reflected in HA.  
- Entities are updated in real time (coordinator refresh every 2s).  

---

## 🔧 Installation

### Option A — HACS (recommended)
1. Make sure you have [HACS](https://hacs.xyz/) installed in Home Assistant.
2. In Home Assistant: **HACS → Integrations → ⋮ (three dots) → Custom repositories**.  
   Add `https://github.com/Sanji78/listonic` as **Category: Integration**.
3. Find **Listonic** in HACS and click **Download**.
4. **Restart** Home Assistant.

### Option B — Manual
1. Copy the folder `custom_components/listonic` from this repository into your Home Assistant config folder:
   - `<config>/custom_components/listonic`
2. **Restart** Home Assistant.

---

## ⚙️ Configuration

### Step 1 — Create a Google OAuth Application
1. Go to [Google Cloud Console](https://console.cloud.google.com/).  
2. Create a new project (or select an existing one).  
3. Navigate to **APIs & Services → Credentials**.  
4. Click **Create Credentials → OAuth client ID**.  
5. Choose **Web application**.  
6. Add **Authorized redirect URI**:  
   ```
   https://my.home-assistant.io/redirect/oauth
   ```
7. Save and copy your **Client ID** and **Client Secret**.

### Step 2 — Add Application Credentials in HA
1. In Home Assistant: **Settings → Devices & Services → Application Credentials**.  
2. Add a new credential:  
   - Domain: `listonic`  
   - Client ID / Secret: from Google console.  

### Step 3 — Add the Integration
1. Home Assistant → **Settings → Devices & services → Add Integration**.  
2. Search for **Listonic**.  
3. Login with your **Google account** to authorize Listonic.  
4. On success, all your shopping lists appear as To-Do lists in HA.

---

## 📋 Entities

- **To-Do lists**: one for each Listonic shopping list.  
  - Items = shopping items  
  - Status = checked / unchecked  
- All lists are dynamically kept in sync:
  - Renaming a list → updates in HA  
  - Adding/removing items → updates both in HA and app  
  - Checking items → reflected everywhere  

You can manage shopping lists entirely from the **To-Do UI** in Home Assistant.

---

## 🔧 Usage Examples

You can use the following services in automations or scripts:

### Create a new list
```yaml
service: listonic.create_list
data:
  name: "Weekend Shopping"
```

### Delete a list
```yaml
service: listonic.delete_list
data:
  list_id: "195112844"
```

### Update a list name
```yaml
service: listonic.update_list
data:
  list_id: "195112844"
  name: "Groceries"
```

### Add an item to a list
```yaml
service: listonic.add_item
data:
  list_id: "195112844"
  name: "Milk"
```

### Delete items from a list
```yaml
service: listonic.delete_items
data:
  list_id: "195112844"
  ids: [12345, 67890]
```

### Update an item (rename or check/uncheck)
```yaml
service: listonic.update_item
data:
  list_id: "195112844"
  id: 12345
  name: "Organic Milk"
  checked: true
```

### Refresh all lists and items manually
```yaml
service: listonic.refresh_data
```

---

## 🧪 Supported versions
- Home Assistant: **2024.8** or newer (earlier may work, untested).

---

## 🐞 Troubleshooting
- Check **Settings → System → Logs** for messages under `custom_components.listonic`.  
- If OAuth login fails, verify that the redirect URL matches exactly:  
  ```
  https://my.home-assistant.io/redirect/oauth
  ```
- If lists don’t appear, try the **`listonic.refresh_data`** service.  

---

## 🙌 Contributing
PRs and issues are welcome. Please open an issue with logs if you hit a bug.

---

## ❤️ Donate
If this project helps you, consider buying me a coffee:  
**[PayPal](https://www.paypal.me/elenacapasso80)**.

..and yes... 😊 the paypal account is correct. Thank you so much!

---

## 📜 License
[MIT](LICENSE.md)
