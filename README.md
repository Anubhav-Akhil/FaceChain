# 🧠 FaceChain — Biometric Intelligence & Blockchain Verification

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Ethereum Sepolia](https://img.shields.io/badge/Ethereum-Sepolia_Testnet-627EEA.svg?style=for-the-badge&logo=ethereum&logoColor=white)](https://sepolia.etherscan.io/)
[![Solidity 0.8.19](https://img.shields.io/badge/Solidity-0.8.19-363636.svg?style=for-the-badge&logo=solidity&logoColor=white)](https://soliditylang.org/)
[![OpenCV DNN](https://img.shields.io/badge/OpenCV-DNN_Face_Detect-5C3EE8.svg?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![Google Lens](https://img.shields.io/badge/Google_Lens-SerpAPI-4285F4.svg?style=for-the-badge&logo=google&logoColor=white)](https://serpapi.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**HH Goa 2026 — Task 3**  
*Developed by **Anubhav Akhil** ([meanubhavakhil@gmail.com](mailto:meanubhavakhil@gmail.com))*

---

## 🌟 Executive Summary

**FaceChain** is an end-to-end biometric identity verification pipeline that combines deep learning computer vision, web-scale reverse image search, and Ethereum smart contracts. 

It takes an input face (via image upload or live webcam), detects facial regions and computes high-dimensional perceptual encodings, tracks the face's digital footprint across the public web and social media via Google Lens, generates a cryptographic SHA-256 data hash, and anchors immutable proof onto the **Ethereum Sepolia Blockchain**.

```
📷 Image / 📹 Webcam ──▶ 🧠 Face Detection ──▶ ☁️ Cloud Upload ──▶ 🔍 Google Lens ──▶ ⛓️ Blockchain ──▶ ✅ On-Chain Verified
```

---

## 🏗️ Architecture & Pipeline Flow

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Input Source  │──────▶│ Face Detection  │──────▶│  Image Hosting  │
│  Image / Webcam │       │   OpenCV DNN    │       │     ImgBB CDN   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                   │                         │
                          128-d perceptual            Public URL for
                             encoding                Google Lens indexing
                                   │                         │
                                   ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    On-Chain     │◀──────│   Blockchain    │◀──────│  Reverse Search │
│  Verification   │       │ Ethereum Sepolia│       │   Google Lens   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
 Immutable ledger audit    SHA-256 Hash Anchor      Visual match discovery
   Tamper-proof check       Duplicate check          Social media priority
```

### The 5 Pipeline Stages

| Stage | Name | Technology | Functional Description |
|---|---|---|---|
| **1** | **Face Detection & Encoding** | OpenCV Deep Neural Network (DNN) / Haar | Detects face landmarks, bounds region, crops face with margin, and extracts 128-d perceptual biometric vectors with zero C++ compilation dependencies. |
| **2** | **Image Upload** | ImgBB REST API | Uploads cropped facial query to obtain a high-speed public CDN URL required for visual indexing. |
| **3** | **Reverse Image Search** | SerpAPI (Google Lens Engine) | Scans Google Lens visual graph across billions of web pages; filters and prioritizes social media profiles (Instagram, LinkedIn, Reddit, X/Twitter, etc.). |
| **4** | **Blockchain Registration** | Solidity 0.8.19 + `web3.py` | Computes a cryptographic SHA-256 hash from query data and writes an immutable record to Ethereum Sepolia. Includes on-chain duplicate detection to prevent redundant transactions and save gas. |
| **5** | **On-Chain Verification** | Ethereum View Calls (`web3.py`) | Reads back the record directly from the smart contract mapping, verifies SHA-256 integrity, registrant address, and timestamp. |

---

## 📜 Smart Contract & On-Chain Ledger

- **Network:** Ethereum Sepolia Testnet (Chain ID: `11155111`)
- **Smart Contract Address:** [`0x53f3451AC38F101c7faE5F252b30B24b29A0d644`](https://sepolia.etherscan.io/address/0x53f3451AC38F101c7faE5F252b30B24b29A0d644)
- **Deployment Tx:** [`0x607619015d2ce54fa807db82d8024d80fe82f87de3fdc459d90302f8a0c92568`](https://sepolia.etherscan.io/tx/0x607619015d2ce54fa807db82d8024d80fe82f87de3fdc459d90302f8a0c92568)
- **Verified Match Tx:** [`0xecdc3277f807c469a6958ad427c82039f31a084dbbb28c839443eaf14fe2c899`](https://sepolia.etherscan.io/tx/0xecdc3277f807c469a6958ad427c82039f31a084dbbb28c839443eaf14fe2c899)

### Contract Interface (`FaceVerification.sol`)

```solidity
struct MatchRecord {
    address registrant;     // Wallet address that registered the match
    uint256 timestamp;      // Block timestamp of registration
    string  imageURL;       // Public URL of the searched face
    string  matchSource;    // Top URL / domain of matched profile
    string  matchTitle;     // Headline / snippet from the match
    bool    exists;         // Existence flag
}

function registerMatch(bytes32 _dataHash, string calldata _imageURL, string calldata _matchSource, string calldata _matchTitle) external;
function verifyMatch(bytes32 _dataHash) external view returns (bool);
function getRecord(bytes32 _dataHash) external view returns (address registrant, uint256 timestamp, string memory imageURL, string memory matchSource, string memory matchTitle);
```

---

## 🎨 Dual User Interface

### 1. Modern Web Application (Flask + Real-Time SSE)
- **Purple Fluid Wave Hero Section**: Designed with multi-layered organic SVG wave curves and modern typography (Google Font Poppins).
- **Interactive Top Navigation**:
  - 🛡️ **Shield**: Smooth scrolls to Verification Pipeline with highlight pulse.
  - 📞 **Phone**: Opens Contact & Support Modal with 1-click email copy.
  - ✉️ **Mail**: Direct link to `meanubhavakhil@gmail.com`.
  - 🔗 **Share**: Native device Web Share API + fallback clipboard copy with toast notifications.
  - 🌐 **Globe**: Direct link to smart contract on Sepolia Etherscan.
- **Real-Time Progress Stepper**: Active step rings, flowing animated gradient streams (`progressFlow`), and live 0% → 100% completion bar.
- **Results Dashboard**: Detailed breakdown of face detection, CDN hosting, top search hit, gas metrics, block numbers, and verification status.
- **Visual Match Gallery**: Responsive gallery grid of web/social media matches discovered by Google Lens, with category filter tabs (`All`, `Social Media`, `Web`).

### 2. High-Performance CLI & Live Webcam
- **File Input Mode**: Fast batch-friendly CLI processing.
- **Live Webcam Mode (`--webcam`)**: Real-time camera feed with bounding box overlays, confidence score HUD, and on-demand `SPACE` key pipeline execution.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9, 3.10, 3.11, 3.12, 3.13, or 3.14
- Web browser (Chrome, Firefox, Edge, Safari)
- Sepolia testnet ETH (free from [sepoliafaucet.com](https://sepoliafaucet.com/))

### 1. Clone the Repository

```bash
git clone https://github.com/Anubhav-Akhil/FaceChain.git
cd FaceChain
```

### 2. Install Dependencies

```bash
# Windows
py -m pip install -r requirements.txt

# Linux / macOS
python3 -m pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the `.env.example` file to `.env`:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` with your API credentials:

```env
SERPAPI_KEY=your_serpapi_key_here
IMGBB_API_KEY=your_imgbb_api_key_here
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/your_alchemy_key
PRIVATE_KEY=your_ethereum_wallet_private_key
CONTRACT_ADDRESS=0x53f3451AC38F101c7faE5F252b30B24b29A0d644
```

*All external services offer generous free tiers:*
- **SerpAPI:** 250 searches/month free ([serpapi.com](https://serpapi.com))
- **ImgBB:** Free image hosting API ([api.imgbb.com](https://api.imgbb.com))
- **Alchemy:** Free Sepolia node RPC ([alchemy.com](https://www.alchemy.com))
- **MetaMask:** Test wallet for signing ([metamask.io](https://metamask.io))

---

## 💻 Running the Application

### Option A: Launch the Web UI (Recommended)

```bash
# Start the Flask development server
py app.py        # Windows
python3 app.py   # Linux / macOS
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

1. Drag and drop any image containing a face into the upload zone.
2. Select your face detection model (`DNN` for high accuracy, `Haar` for speed).
3. Click **🚀 Run Pipeline**.
4. Watch the progress bar advance through all 5 stages in real time!

---

### Option B: Run via Command Line Interface (CLI)

```bash
# Run pipeline with a local image file
py run_pipeline.py --image sample_images/input.jpg

# Save output to JSON
py run_pipeline.py -i sample_images/input.jpg --output results.json

# Run with verbose debugging
py run_pipeline.py -i sample_images/input.jpg --verbose
```

### Option C: Live Webcam Mode

```bash
py run_pipeline.py --webcam
```

- **`SPACE`**: Capture current frame and launch the verification pipeline.
- **`Q` / `ESC`**: Quit webcam mode.

---

## 📂 Repository Structure

```
FaceChain/
├── app.py                     # Flask web server & SSE stream controller
├── run_pipeline.py            # Command-line interface entry point
├── deploy_contract.py         # Smart contract deployment script
├── requirements.txt           # Python package dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Excluded files (keys, bytecode, uploads)
├── README.md                  # Project documentation
│
├── contracts/
│   ├── FaceVerification.sol  # Solidity 0.8.19 smart contract
│   └── abi.json               # Compiled contract Application Binary Interface
│
├── src/
│   ├── __init__.py            # Package initialization
│   ├── pipeline.py            # Pipeline orchestrator & SSE event streamer
│   ├── blockchain.py          # Web3 client, duplicate checks & verification
│   ├── face_detector.py       # OpenCV DNN & Haar face detection & encoding
│   ├── image_uploader.py      # ImgBB CDN upload client
│   ├── reverse_search.py      # Google Lens reverse search via SerpAPI
│   ├── webcam.py              # Real-time webcam capture with HUD overlay
│   └── utils.py               # Cryptographic hashing & config utilities
│
├── templates/
│   └── index.html             # Main frontend template with purple wave hero
│
└── static/
    ├── style.css              # Custom CSS design system (fluid waves, SaaS cards)
    └── app.js                 # Drag-drop, SSE streaming, gallery & modals
```

---

## 🛡️ Security & Integrity Highlights

- **Pre-Execution Smart Contract Checks**: Before broadcasting a transaction, FaceChain checks whether the computed hash already exists on-chain. If previously registered, it prevents transaction reversion and avoids unnecessary gas fees while confirming on-chain integrity.
- **Cryptographic Tamper-Evidence**: If even a single byte of the matched source URL, title, or image URL is modified, the SHA-256 hash recalculation fails verification against the smart contract record.
- **Environment Safety**: Private keys and API tokens are restricted to `.env` and excluded from source control.

---

## 👨‍💻 Author & Contact

- **Developer:** Anubhav Akhil
- **Email:** [meanubhavakhil@gmail.com](mailto:meanubhavakhil@gmail.com)
- **GitHub:** [@Anubhav-Akhil](https://github.com/Anubhav-Akhil)
- **Project:** [FaceChain on GitHub](https://github.com/Anubhav-Akhil/FaceChain)
- **Hackathon:** HH Goa 2026 — Task 3

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — see the LICENSE file for details.
