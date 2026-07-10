# Dell iDRAC for Home Assistant

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/U7U21VQTGJ)

A Home Assistant custom integration to **monitor** and **control** Dell PowerEdge servers through iDRAC — fan speed, server power, and telemetry (temperatures, fan RPM, power draw, PSUs, inventory). Uses Redfish for telemetry and pure-Python IPMI RMCP+ for fan and power commands — no `ipmitool` binary required.

## Features

| Category | Details |
|----------|---------|
| **Telemetry (Redfish)** | System model, power state, BIOS version, service tag, CPU, memory, temperatures, fan RPM, power consumption, PSU voltages |
| **Fan Control (IPMI)** | Single dropdown — `Auto` (Dell automatic curve) or a fixed speed in 10 % steps (10 %–100 %) |
| **Power Control (IPMI)** | Explicit power action buttons — Power On, Graceful Shutdown (ACPI), Force Off, Power Cycle, Hard Reset — with a read-only Power State sensor. Buttons grey out when they can't apply (eg Power On while already on) |
| **Platforms** | `sensor`, `select` (fan speed), `button` (power actions) |
| **Config Flow** | UI-based setup with connection validation |
| **Options Flow** | Adjust scan interval, Redfish base path, TLS settings, timeouts, and power-off mode after initial setup |
| **Localisation** | English, Traditional Chinese (zh-Hant) |

## Requirements

- Dell server with **iDRAC** (tested on iDRAC 7/8/9)
- Redfish API enabled (HTTPS, default port 443)
- IPMI over LAN enabled (UDP, default port 623)
- Home Assistant **2024.1** or later

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rztw&repository=dell-fans-ipmi-ha&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dell_idrac)
1. Open **HACS** in Home Assistant.
2. Click **Integrations** → **⋮** (top-right) → **Custom repositories**.
3. Paste the repository URL and select category **Integration**.
4. Search for **Dell iDRAC** and install.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/dell_idrac` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Dell iDRAC**.
3. Enter your iDRAC host/IP, credentials, and (optionally) the IPMI port.
4. The integration validates the connection via Redfish before creating the entry.

### Options

After setup, click **Configure** on the integration card to adjust:

| Option | Default | Description |
|--------|---------|-------------|
| Scan interval | 30 s | How often to poll Redfish and probe IPMI |
| Redfish base path | `/redfish/v1` | Override if your iDRAC uses a non-standard path |
| Allow insecure TLS | Yes | Skip certificate verification (common for self-signed iDRAC certs) |
| Redfish timeout | 15 s | HTTP request timeout |
| IPMI timeout | 5 s | UDP session timeout |

## Entities

### Sensors (Redfish telemetry)

- **Model** / **Service Tag** / **BIOS Version** / **CPU Model** / **Total Memory** — diagnostic
- **Power State** — On / Off / …
- **iDRAC Firmware** — diagnostic
- **Power Consumption** / **Average Power** / **Peak Power** — watts
- **\<Fan Name\>** — RPM per fan (dynamic, one entity per fan)
- **\<Temperature Name\>** — °C per sensor (dynamic, one entity per temperature reading)
- **\<PSU Name\>** — input voltage per power supply (dynamic)

### Controls (IPMI)

- **Fan Speed** (`select`) — one dropdown: `Auto` restores Dell's automatic fan curve; picking a percentage (10 %–100 %) sets that fixed speed. After a change, the per-fan RPM sensors are refreshed within a few seconds so you can confirm it took effect
- **Power State** (`sensor`) — On / Off, from IPMI Get Chassis Status (fast and reliable; not dependent on Redfish)
- **Power On** / **Graceful Shutdown** (`button`) — the everyday pair. Graceful Shutdown is an ACPI soft shutdown that lets the OS close cleanly. Each greys out when it can't apply (Power On while on, shutdown while off)
- **Force Off** / **Power Cycle** / **Hard Reset** (`button`) — abrupt actions. IPMI has no graceful restart, so restarts are always abrupt

> **Confirmation prompts:** Home Assistant can't enforce an "are you sure?" dialog from the integration itself. To guard against accidental presses, add a confirmation to the dashboard card's tap action:
>
> ```yaml
> tap_action:
>   action: perform-action
>   perform_action: button.press
>   target:
>     entity_id: button.dell_idrac_HOST_graceful_shutdown
>   confirmation:
>     text: "Shut down the server?"
> ```

## How It Works

```
Home Assistant
  ├── TelemetryCoordinator ──► Redfish HTTPS ──► iDRAC
  └── FanControlCoordinator ─► IPMI RMCP+ UDP ──► iDRAC
```

- **Redfish** reads system, manager, thermal, and power data via HTTPS Basic Auth. iDRAC's Redfish stack is slow, so each poll fetches only the **dynamic** Thermal and Power resources (2 requests); static inventory (model, BIOS, iDRAC firmware, etc) is fetched once and cached, resource paths are resolved once, requests retry on transient failures, and a slow section falls back to its previous values so one timeout doesn't blank every entity.
- **Power State** is read over IPMI (Get Chassis Status) rather than Redfish, since IPMI responds in ~0.1 s versus several seconds for Redfish on iDRAC8.
- **IPMI** uses a pure-Python RMCP+ implementation (AES-128-CBC + HMAC-SHA256/SHA1) to send Dell OEM raw commands for fan control and chassis power control — no external binaries needed.

## License

[MIT](LICENSE)

## Disclaimer

Dell, the Dell logo, iDRAC, PowerEdge, and Redfish are trademarks or registered trademarks of Dell Technologies Inc. or its subsidiaries. This project is not affiliated with, endorsed by, or sponsored by Dell Technologies Inc. All trademarks are the property of their respective owners.

---

## 正體中文版本

# Dell iDRAC（Home Assistant）

這是一個 Home Assistant 自訂整合，透過 iDRAC **監控**與**控制** Dell PowerEdge 伺服器 — 風扇轉速、伺服器電源，以及遙測（溫度、風扇 RPM、功耗、PSU、硬體資訊）。遙測資料使用 Redfish，風扇與電源控制使用純 Python 的 IPMI RMCP+，不需要 `ipmitool` 可執行檔。

## 功能

| 類別 | 說明 |
|------|------|
| **遙測（Redfish）** | 系統型號、電源狀態、BIOS 版本、Service Tag、CPU、記憶體、溫度、風扇 RPM、功耗、PSU 電壓 |
| **風扇控制（IPMI）** | 單一下拉選單 — `Auto`（Dell 自動曲線）或固定轉速，以 10% 為級距（10%–100%） |
| **電源控制（IPMI）** | 明確的電源動作按鈕 — 開機、正常關機（ACPI）、強制關機、電源循環、強制重置 — 搭配唯讀的電源狀態感測器。按鈕在不適用時會變灰（例如已開機時的「開機」） |
| **平台** | `sensor`、`select`（風扇轉速）、`button`（電源動作） |
| **設定流程** | 支援 UI 設定，建立時會先驗證連線 |
| **選項流程** | 可在安裝後調整輪詢間隔、Redfish 路徑、TLS 設定與逾時 |
| **在地化** | 英文、正體中文（zh-Hant） |

## 需求

- 具備 **iDRAC** 的 Dell 伺服器（已在 iDRAC 7/8/9 驗證）
- 已啟用 Redfish API（HTTPS，預設連接埠 443）
- 已啟用 IPMI over LAN（UDP，預設連接埠 623）
- Home Assistant **2024.1** 或更新版本

## 安裝

### 透過 HACS（建議）

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rztw&repository=dell-fans-ipmi-ha&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dell_idrac)
1. 在 Home Assistant 開啟 **HACS**。
2. 進入 **Integrations** → 右上角 **⋮** → **Custom repositories**。
3. 貼上此專案的 repository URL，類型選擇 **Integration**。
4. 搜尋 **Dell iDRAC** 並安裝。
5. 重新啟動 Home Assistant。

### 手動安裝

1. 將 `custom_components/dell_idrac` 複製到 Home Assistant 的 `config/custom_components/`。
2. 重新啟動 Home Assistant。

## 設定

1. 前往 **設定** → **裝置與服務** → **新增整合**。
2. 搜尋 **Dell iDRAC**。
3. 輸入 iDRAC 主機/IP、帳號密碼（可選填 IPMI 連接埠）。
4. 整合會先以 Redfish 驗證連線，通過後才建立設定。

### 可調整選項

完成設定後，可在整合卡片按 **Configure** 調整：

| 選項 | 預設值 | 說明 |
|------|--------|------|
| 輪詢間隔 | 30 秒 | Redfish 輪詢與 IPMI 探測頻率 |
| Redfish base path | `/redfish/v1` | 若 iDRAC 使用非標準路徑可覆寫 |
| 允許不安全 TLS | 是 | 跳過憑證驗證（常見於自簽章憑證） |
| Redfish 逾時 | 15 秒 | HTTP 請求逾時 |
| IPMI 逾時 | 5 秒 | UDP Session 逾時 |

## 實體（Entities）

### 感測器（Redfish 遙測）

- **Model** / **Service Tag** / **BIOS Version** / **CPU Model** / **Total Memory**（診斷）
- **Power State**（電源狀態）
- **iDRAC Firmware**（診斷）
- **Power Consumption** / **Average Power** / **Peak Power**（瓦特）
- **\<Fan Name\>**：每個風扇一個 RPM 感測器（動態建立）
- **\<Temperature Name\>**：每個溫度點一個 °C 感測器（動態建立）
- **\<PSU Name\>**：每個電源供應器一個輸入電壓感測器（動態建立）

### 控制（IPMI）

- **Fan Speed**（`select`）：單一下拉選單；`Auto` 恢復 Dell 自動風扇曲線，選擇百分比（10%–100%）則設定該固定轉速。變更後會在數秒內刷新各風扇 RPM 感測器，方便確認已生效
- **Power State**（`sensor`）：On / Off，取自 IPMI Get Chassis Status（快速可靠，不依賴 Redfish）
- **Power On** / **Graceful Shutdown**（`button`）：日常使用的一組。正常關機為 ACPI 軟關機，讓作業系統乾淨關閉。各按鈕在不適用時會變灰（已開機時的「開機」、已關機時的關機）
- **Force Off** / **Power Cycle** / **Hard Reset**（`button`）：較激烈的動作。IPMI 沒有正常重啟，因此重啟一律為強制

> **確認提示：** Home Assistant 無法由整合本身強制彈出「確定嗎？」對話框。為避免誤觸，可在儀表板卡片的 tap action 加入確認：
>
> ```yaml
> tap_action:
>   action: perform-action
>   perform_action: button.press
>   target:
>     entity_id: button.dell_idrac_HOST_graceful_shutdown
>   confirmation:
>     text: "確定要關閉伺服器嗎？"
> ```

## 運作方式

```
Home Assistant
  ├── TelemetryCoordinator ──► Redfish HTTPS ──► iDRAC
  └── FanControlCoordinator ─► IPMI RMCP+ UDP ──► iDRAC
```

- **Redfish**：透過 HTTPS Basic Auth 讀取 system、manager、thermal、power 資料。
- **IPMI**：透過純 Python RMCP+（AES-128-CBC + HMAC-SHA256/SHA1）送出 Dell OEM 原生命令進行風扇控制，不需外部二進位工具。

## 免責聲明

Dell、Dell 標誌、iDRAC、PowerEdge 及 Redfish 為 Dell Technologies Inc. 或其子公司的商標或註冊商標。本專案與 Dell Technologies Inc. 無任何關聯、背書或贊助關係。所有商標均為其各自所有者之財產。
