# ThermaBrain 🧠🔥

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

**ThermaBrain** is an advanced AI/ML-driven medical imaging and thermal analysis framework designed for neurological diagnosis and thermal anomaly detection. By integrating deep learning architectures with computer vision processing pipelines, ThermaBrain assists in detecting, analyzing, and visualizing thermal patterns and structural irregularities.

---

## 🏗️ Project Architecture

ThermaBrain follows a modular, end-to-end processing pipeline designed to handle thermal image ingestion, feature extraction, deep learning inference, and visualization.

```
ThermaBrain/
│
├── data/                  # Raw and preprocessed dataset directories
│   ├── raw/               # Original thermal scans & images
│   └── processed/         # Normalized and segmented tensors
│
├── models/                # Saved weights, serialized checkpoints, and architecture definitions
│
├── notebooks/             # Exploratory Data Analysis (EDA) and experiment logs
│
├── src/                   # Core application source code
│   ├── preprocessing/     # Image normalization, resizing, noise reduction, and augmentation
│   ├── models/            # CNN / Neural Network implementations and backbone setups
│   ├── inference/         # Prediction engine and evaluation metrics
│   └── utils/             # Helper utilities, logging, and plotting scripts
│
├── api/                   # Backend web service / REST API (FastAPI / Flask)
├── tests/                 # Unit and integration tests
├── requirements.txt       # Python package dependencies
├── Dockerfile             # Container configuration for reproducible deployments
└── README.md              # Project documentation
```

### 🔄 System Data Flow

```
+--------------------+      +-----------------------+      +------------------------+
|  Thermal / Image   | ---> |  Data Preprocessing   | ---> |  Deep Learning Engine  |
|     Ingestion      |      | (Normalize/Transform) |      | (CNN/Segmentation Model|
+--------------------+      +-----------------------+      +------------------------+
                                                                       |
                                                                       v
+--------------------+      +-----------------------+      +------------------------+
|   Visualization    | <--- |     REST API / CLI    | <--- |   Anomalies & Heatmaps |
| (Web Dashboard/UI) |      |        Interface      |      |       Generation       |
+--------------------+      +-----------------------+      +------------------------+
```

---

## ⚙️ Tech Stack

### **Core Programming & Machine Learning**
* **Language:** Python 3.8+
* **Deep Learning Frameworks:** PyTorch / TensorFlow / Keras
* **Computer Vision & Image Processing:** OpenCV, Scikit-Image, PIL (Pillow)
* **Data Processing & Analysis:** NumPy, Pandas, Scikit-learn

### **API & Web Deployment**
* **API Framework:** FastAPI / Flask
* **Server Middleware:** Uvicorn / Gunicorn

### **Visualization & Utilities**
* **Plotting & Analytics:** Matplotlib, Seaborn
* **Environment & Package Management:** Virtualenv / Conda

---

## 🚀 Quick Start & Installation

### Prerequisites
* Python 3.8 or higher installed on your system
* Git
* CUDA-compatible GPU *(Optional, for accelerated model inference/training)*

### Step-by-Step Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gauravnegigit/ThermaBrain.git
   cd ThermaBrain
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate

   # On Windows:
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run Model Inference or API Service:**
   ```bash
   # Run prediction pipeline
   python src/inference/predict.py --input data/raw/sample_scan.png

   # Or launch API server (if using FastAPI)
   uvicorn api.main:app --reload
   ```

---

## 🧪 Running Tests

To execute the unit tests for data preprocessing and inference modules:
```bash
pytest tests/
```

---

## 🤝 Contributing

Contributions are welcome! Follow these steps to contribute:
1. Fork the Repository
2. Create a Feature Branch (`git checkout -b feature/NewFeature`)
3. Commit your Changes (`git commit -m 'Add NewFeature'`)
4. Push to the Branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.