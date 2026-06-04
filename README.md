# Mini SOC Architecture: Wazuh SIEM Deployment & DDoS Attack Simulation
Deskripsi Tugas: Melakukan *deployment* arsitektur SIEM Wazuh di dalam VM cloud Azure, menyimulasikan skenario serangan *Distributed Denial of Service* (DDoS), serta melakukan optimasi kepadatan dan distribusi penyimpanan log (*logging density & distribution*).

## Anggota Kelompok
| Nama | NRP | Role |
|------|------|------|
| Muhammad Fatihul Qolbi Ash-Shiddiqi | 5027241023 | Shuffle Manager |
| Muhammad Ahsani Taqwiim Rahman | 5027241099 | Wazuh Agent |
| Imam Mahmud Dalil Fauzan | 5027241100 | Wazuh Manager |
| Naufal Ardhana | 5027241118 | Attacker |

## Arsitektur Sistem
Menggunakan 3 Mesin Virtual (VM) di Azure:

```text
               [ VM Wazuh Manager (Fauzan) ]
                             │ (HTTPS Port 443)
                             ▼
                  ┌──────────────────────┐
                  │ Wazuh Manager (VM 1) │
                  │  (Standard_D2s_v3)   │
                  └──────────▲───────────┘
                             │
            ┌────────────────┴────────────────┐
   (Port 1514/1515)                  (Port 1514/1515)
            │                                 │
┌───────────────────────┐         ┌───────────────────────┐
│  Wazuh Agent (VM 2)   │         │  Wazuh Agent (VM 3)   │
│   Target / Web Srv    │         │       Attacker        │
│      (Obi's VM)       │         │     (Ardhan's VM)     │
└───────────────────────┘         └───────────────────────┘
```
### Spesifikasi Infrastruktur Azure
| Nama VM | Peran | OS | Spesifikasi | Komponen Utama |
|----------|--------|----|--------------|----------------|
| azurevm-manager | SIEM Central Server | Ubuntu 22.04 LTS | Standard_D2s_v3 (2 vCPU, 8 GB RAM) | Wazuh Manager, Indexer, Dashboard |
| azurevm-agent-obi | Target Host / Victim | Ubuntu 22.04 LTS | Standard_B1s (1 vCPU, 1 GB RAM) | Wazuh Agent, Apache2 Web Server |
| azurevm-attacker | Threat Actor | Ubuntu 22.04 LTS | Standard_B1s (1 vCPU, 1 GB RAM) | Wazuh Agent, hping3 Network Tool |

## Panduan Deployment & Instalasi
1. Setup Jaringan & Aturan Keamanan (Azure NSG)
Pada azurevm-manager-nsg, dikonfigurasi Inbound Security Rules berikut untuk memastikan kelancaran akses dan pengiriman data log:
  - Port 22 (SSH): Untuk manajemen remote server via terminal.
  - Port 443 (HTTPS): Untuk mengakses Web Interface/Dashboard Wazuh.
  - Port 1514-1515 (TCP): Untuk komunikasi enkripsi dan registrasi otomatis (enrollment) dari kedua Wazuh Agent ke Manager.
2. Instalasi Wazuh Manager (Fauzan)
Menggunakan metode One-Liner Assistant resmi pada VM Manager:
```bash
curl -sO [https://packages.wazuh.com/4.9/wazuh-install.sh](https://packages.wazuh.com/4.9/wazuh-install.sh) && sudo bash wazuh-install.sh -a
```
3. Setup Target Web Server & Agent (Obi)
Mengaktifkan layanan HTTP sebagai target dan menghubungkannya ke SIEM:
```bash
# Instalasi Web Server
sudo apt update && sudo apt install apache2 -y
sudo systemctl start apache2

# Instalasi Agent (Mengikuti instruksi 'Deploy new agent' dari Dashboard)
curl -s [https://packages.wazuh.com/key/GPG-KEY-WAZUH](https://packages.wazuh.com/key/GPG-KEY-WAZUH) | gpg --dearmor -o /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] [https://packages.wazuh.com/4.x/apt/](https://packages.wazuh.com/4.x/apt/) stable main" | sudo tee /etc/apt/sources.list.get/wazuh.list
sudo apt-get update && WAZUH_MANAGER='<IP_PUBLIK_MANAGER>' IP_SELECTOR='json' apt-get install wazuh-agent -y
sudo systemctl start wazuh-agent
```

## Skenario & Eksekusi DDoS Attack (PoC)
Skenario ini membuktikan kapabilitas Proof of Concept (PoC) deteksi SIEM terhadap anomali trafik tinggi (SYN Flood Attack).

1. Tuning Kustom Aturan Deteksi (Wazuh Manager)
Untuk mempercepat respon terhadap lonjakan trafik skala lab mahasiswa, ditambahkan aturan kustom pada `/var/ossec/etc/rules/local_rules.xml`:
```xml
<rule id="100001" level="12">
  <if_matched_sid>31100</if_matched_sid>
  <same_source_ip />
  <description>DDoS Attack Detected: High volume of connection attempts from a single IP</description>
  <mitre>
    <id>T1498.001</id>
  </mitre>
</rule>
```

2. Peluncuran Serangan (Ardhan)
Ardhan meluncurkan banjir paket `SYN` ke port 80 milik Obi menggunakan `hping3`:
## Attacker Node — azurevm-agent

Node ini berperan sebagai mesin penyerang dalam skenario pengujian SIEM Wazuh. Serangan dijalankan dari `azurevm-agent` ke target `VM2MIKS` yang berada dalam satu VNet Azure yang sama.

---

### Skenario 1 — HTTP Flood (DDoS Layer 7)

**Tool:** ApacheBench (`ab`)

**Instalasi:**
```bash
sudo apt update && sudo apt install -y apache2-utils
```

**Command serangan:**
```bash
ab -n 1000 -c 100 http://<TARGET_IP>/
```

| Parameter | Nilai | Penjelasan |
|-----------|-------|------------|
| `-n` | 1000 | Total HTTP request yang dikirimkan |
| `-c` | 100 | Jumlah koneksi concurrent (serentak) |
| Target | `<TARGET_IP>` | IP publik VM2MIKS yang menjalankan Apache |

Serangan ini memicu alert **Rule ID 100210 Level 12** di Wazuh dengan deskripsi *ApacheBench HTTP flood detected against web server target*.

---

### Skenario 2 — Simulasi Malware (EICAR Test File)

**Tool:** ClamAV

EICAR adalah file test standar industri yang dikenali antivirus sebagai malware tanpa berbahaya secara nyata.

**Instalasi ClamAV di VM target:**
```bash
sudo apt install -y clamav clamav-daemon
sudo systemctl stop clamav-freshclam
sudo freshclam
sudo systemctl start clamav-freshclam
```

**Membuat EICAR file dan scan:**
```bash
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar_test.com
sudo clamscan --infected --remove /tmp/eicar_test.com
```

ClamAV mendeteksi `Eicar-Signature FOUND` dan melaporkan ke Wazuh, memicu alert **Rule ID 52502** — *ClamAV: Virus detected*.

---

### Kronologi Serangan

| Waktu | Aksi | Tool | Alert Wazuh |
|-------|------|------|-------------|
| 09:44 | Credential brute-force | Hydra v9.5 | Rule 5710, Level 5 |
| 15:39 | HTTP Flood ke VM2MIKS | ApacheBench | Rule 100210, Level 12 |
| 10:18 | Simulasi malware EICAR | ClamAV | Rule 52502, Level 7 |

---

> Seluruh serangan dilakukan dalam lingkungan lab terisolasi pada Microsoft Azure Student Free Tier.

3. Dampak Serangan
  - Sisi Target (Obi): CPU Load melonjak drastis mencapai ~100% dan service web Apache menjadi lambat/unreachable (Denial of Service).
  
  - Sisi SIEM (Fauzan): Aturan kustom ID `100001` langsung terpicu, menghasilkan Alert Level 12 (High Severity) secara real-time di Dashboard dengan indikasi IP penyerang yang akurat.

## Manajemen Kepadatan & Distribusi Log
Karena keterbatasan kapasitas penyimpanan (disk storage) pada Azure Student tier, diimplementasikan strategi optimasi berikut:
1. Logging Density Control:
Mengonfigurasi berkas `/var/ossec/etc/ossec.conf` agar hanya menyimpan log yang berguna bagi analisis keamanan keamanan (minimal `log_level` berada pada tingkat 3 ke atas). Trafik normal/informasional level < 3 diabaikan untuk menghemat storage.

2. Log Distribution & Rotation:
Log aktif yang telah expired akan dikompresi menjadi format `.gz` di direktori `/var/ossec/logs/alerts/` untuk menghemat ruang simpan hingga 80%.
