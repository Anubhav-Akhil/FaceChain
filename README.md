# 🧠 Face ID + Blockchain Verification Pipeline

**HH Goa 2026 — Shortlisting Task 3**

An end-to-end Python pipeline that takes a face image as input, identifies matching content on the web/social media via genuine reverse image search, and writes a tamper-evident verification record to the Ethereum blockchain.

```
📷 Face Image → 🧠 Face Detection → 🔍 Reverse Search → ⛓️ Blockchain → ✅ Verified
📹 Webcam     ↗
```

---

## 🏗️ Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Input Image │───▶│ Face Detect  │───▶│ Image Upload │───▶│ Google Lens  │───▶│  Blockchain  │
│  (photo.jpg) │    │ & Encoding   │    │   (ImgBB)    │    │  (SerpAPI)   │    │  (Sepolia)   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                     OpenCV YuNet ONNX   Public URL          Visual matches     SHA-256 hash +
                     128-d vector        for search          Social media       metadata stored
                     + face crop                             prioritized        on-chain
```

### Pipeline Stages

| # | Stage | Technology | What It Does |
|---|-------|-----------|--------------|
| 1 | **Face Detection & Encoding** | OpenCV YuNet ONNX | Detects face(s), extracts 128-dimensional perceptual encoding, crops face with margin |
| 2 | **Image Upload** | ImgBB API | Uploads cropped face to get a public URL (required for Google Lens) |
| 3 | **Reverse Image Search** | SerpAPI (Google Lens) | Genuine reverse image search — finds visually matching web/social media posts |
| 4 | **Blockchain Registration** | `web3.py` + Ethereum Sepolia | Computes SHA-256 hash of match data, stores hash + metadata on-chain |
| 5 | **On-Chain Verification** | `web3.py` read call | Reads back the on-chain record and confirms data integrity |

---

## 📜 Deployed Smart Contract & Proof of Execution

- **Contract Address:** [`0x53f3451AC38F101c7faE5F252b30B24b29A0d644`](https://sepolia.etherscan.io/address/0x53f3451AC38F101c7faE5F252b30B24b29A0d644)
- **Deployment Transaction:** [`0x60761901...`](https://sepolia.etherscan.io/tx/0x607619015d2ce54fa807db82d8024d80fe82f87de3fdc459d90302f8a0c92568)
- **Live Verification Transaction:** [`0xe55d1038...`](https://sepolia.etherscan.io/tx/0xe55d10380435644b615b5a9bab30bb197a9f8df3f1ac66ca222d34b50f12fe40)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (Tested and working on Python 3.14 on Windows)
- **Zero C++ build tool dependencies** (Uses pure OpenCV ONNX DNN)
- **Sepolia Test ETH** (Free from Sepolia faucets)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/HHGOA-T3-FaceID-Blockchain.git
cd HHGOA-T3-FaceID-Blockchain

pip install -r requirements.txt
```

### 2. Get API Keys (all free)

| Service | Sign Up | Free Tier |
|---------|---------|-----------|
| **SerpAPI** | [serpapi.com](https://serpapi.com/) | 250 searches/month |
| **ImgBB** | [api.imgbb.com](https://api.imgbb.com/) | Unlimited uploads |
| **Alchemy** | [alchemy.com](https://www.alchemy.com/) | 30M compute units/month |

### 3. Configure Environment

```bash
# Copy the template
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux

# Edit .env with your keys
```

Fill in your `.env`:
```env
SERPAPI_KEY=<your SerpAPI key>
IMGBB_API_KEY=<your ImgBB key>
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/<your Alchemy key>
PRIVATE_KEY=<your MetaMask private key>
```

### 4. Get Sepolia Test ETH

Visit [sepoliafaucet.com](https://sepoliafaucet.com/) and request free Sepolia ETH to your wallet address. You need a small amount (~0.01 ETH) for gas fees.

### 5. Deploy the Smart Contract

```bash
python deploy_contract.py
```

This will:
- Compile `FaceVerification.sol` using Solidity 0.8.19
- Deploy to Ethereum Sepolia testnet
- Automatically save the contract address to your `.env` file
- Save the compiled ABI to `contracts/abi.json`

### 6. Run the Pipeline

```bash
# From an image
python run_pipeline.py --image path/to/photo.jpg

# From live webcam
python run_pipeline.py --webcam
```

#### CLI Options

| Flag | Description | Default |
|------|------------|---------|
| `--image`, `-i` | Path to input image | — |
| `--webcam`, `-w` | Launch live webcam mode | — |
| `--model`, `-m` | Face detection model: `dnn` (accurate) or `haar` (fast) | `dnn` |
| `--verbose`, `-v` | Enable debug output | `False` |
| `--output`, `-o` | Save results to JSON file | — |

> **Note:** `--image` and `--webcam` are mutually exclusive — use one or the other.

#### Examples

```bash
# Basic usage with an image
python run_pipeline.py --image selfie.jpg

# High-accuracy detection + save results
python run_pipeline.py --image celebrity.png --model dnn --output results.json

# Live webcam mode
python run_pipeline.py --webcam

# Webcam with Haar cascade (faster, less accurate)
python run_pipeline.py --webcam --model haar

# Verbose mode for debugging
python run_pipeline.py -i photo.jpg -v
```

---

## 📹 Live Webcam Mode

The webcam mode opens your camera and provides a real-time face detection overlay.

```bash
python run_pipeline.py --webcam
```

### Controls

| Key | Action |
|-----|--------|
| `SPACE` | Capture current frame and run the full pipeline |
| `Q` / `ESC` | Quit webcam mode |

### Features

- **Real-time face detection** — bounding boxes with confidence scores drawn on every frame
- **HUD overlay** — shows face count, FPS, and controls
- **On-demand pipeline** — press SPACE to trigger the full search + blockchain flow
- **Mirrored preview** — natural selfie-style interaction
- **No extra dependencies** — uses the same OpenCV already installed

---

## ⛓️ Blockchain Details

### Which Blockchain?

**Ethereum Sepolia Testnet** — a public Ethereum test network.

| Property | Value |
|----------|-------|
| Network | Ethereum Sepolia (testnet) |
| Chain ID | 11155111 |
| Currency | SepoliaETH (free, no real value) |
| Explorer | [sepolia.etherscan.io](https://sepolia.etherscan.io/) |

### Smart Contract: `FaceVerification.sol`

The contract stores face-match verification records as on-chain mappings:

```
SHA-256(match_data) → {registrant, timestamp, imageURL, matchSource, matchTitle}
```

**Key functions:**
- `registerMatch(hash, imageURL, matchSource, matchTitle)` — writes a new record (costs gas)
- `verifyMatch(hash)` → `bool` — checks if a record exists (free read)
- `getRecord(hash)` → returns full record details (free read)

### Tamper-Evidence

The pipeline computes a **SHA-256 hash** of the combined match data:
```
hash = SHA-256(JSON({title, link, source, image_url}))
```

This hash is stored on-chain. To verify:
1. Re-compute the hash from the original match data
2. Call `verifyMatch(hash)` on the contract
3. If `true` → data has not been tampered with
4. Call `getRecord(hash)` to retrieve the full stored record

Anyone can verify the record on [Sepolia Etherscan](https://sepolia.etherscan.io/) using the transaction hash.

---

## 📁 Project Structure

```
HHGOA T-3/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # API key template
├── .gitignore                   # Git exclusions
│
├── contracts/
│   ├── FaceVerification.sol     # Solidity smart contract
│   └── abi.json                 # Compiled ABI (generated by deploy script)
│
├── src/
│   ├── __init__.py              # Package init
│   ├── pipeline.py              # Main orchestrator
│   ├── webcam.py                # Live webcam mode with real-time detection
│   ├── face_detector.py         # Stage 1: Face detection & encoding
│   ├── image_uploader.py        # Stage 2: ImgBB upload
│   ├── reverse_search.py        # Stage 3: Google Lens search via SerpAPI
│   ├── blockchain.py            # Stage 4 & 5: Blockchain write + verify
│   └── utils.py                 # Shared helpers (hashing, config, logging)
│
├── deploy_contract.py           # One-time contract deployment
└── run_pipeline.py              # CLI entry point
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| Face Detection | `face_recognition` (dlib) |
| Image Processing | Pillow, OpenCV |
| Image Hosting | ImgBB API |
| Reverse Image Search | SerpAPI (Google Lens engine) |
| Blockchain | Ethereum Sepolia via `web3.py` |
| Smart Contract | Solidity 0.8.19 |
| Contract Compilation | `py-solc-x` |
| CLI | argparse |
| Output | `rich` (colored terminal output) |

---

## ⚠️ Known Limitations

1. **Face Detection Library**
   - `face_recognition` / `dlib` requires C++ build tools and CMake on Windows, which can be tricky to install
   - The HOG model is fast but less accurate for rotated or partially occluded faces; use `--model cnn` for better accuracy

2. **Reverse Image Search**
   - Results depend heavily on the person's online presence — if someone has no photos online, no matches will be found
   - SerpAPI free tier is limited to 250 searches/month
   - Google Lens results may vary by region and over time

3. **Blockchain**
   - Uses Sepolia testnet (not mainnet) — transactions have no real monetary value
   - Requires free Sepolia ETH from a faucet
   - Transaction confirmation takes ~15-30 seconds
   - String data stored on-chain is truncated to 256 characters to manage gas costs

4. **Image Upload**
   - ImgBB is used as a temporary image host — uploaded images may eventually expire
   - The cropped face must be publicly accessible for Google Lens to process it

5. **Privacy**
   - The pipeline uploads face crops to a public image host and sends them to Google
   - On-chain records are publicly visible on the Sepolia blockchain
   - Not suitable for sensitive/private data without additional privacy measures

---

## 📜 License

MIT License — see individual library licenses for dependencies.

---

*Built for HH Goa 2026 Shortlisting Task 3*
