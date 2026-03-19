# 🏠 Smart Home AI Energy Management System

## 🚀 Overview

Smart Home AI is an intelligent energy management system that monitors, predicts, and optimizes household energy consumption **without requiring expensive IoT hardware**.

It combines **AI models, real-time data, and a voice-controlled Android app (Luna)** to provide a complete smart home experience using software-driven solutions.

---

## 🔥 Key Features

* ⚡ **Energy Monitoring** – Track device-wise power usage
* 🧠 **AI Prediction** – Forecast future energy consumption
* 🚨 **Anomaly Detection** – Detect unusual energy spikes
* 🧪 **Device Simulation** – Works even without smart devices
* 🎤 **Voice Control (Luna App)** – Control devices via Android app
* 📊 **Interactive Dashboard** – Built using Streamlit
* ☁️ **Firebase Integration** – Real-time data sync

---

## 🧠 Tech Stack

### Backend (AI + Dashboard)

* Python
* Streamlit
* Machine Learning
* Firebase

### Mobile App (Luna)

* Kotlin
* Android Studio
* Firebase

---

## 📂 Project Structure

```id="project-structure"}
smart-home-ai/
│
├── backend/            # AI + Streamlit Dashboard
├── luna-android/       # Android Voice Assistant App
├── README.md
├── .gitignore
```

---

## ▶️ How to Run

### 🔹 1. Run Backend (Streamlit UI)

```id="run-backend"}
pip install -r backend/requirements.txt
streamlit run backend/app.py
```

👉 Open in browser: `http://localhost:8501`

---

### 🔹 2. Run Android App (Luna)

1. Open `luna-android` in Android Studio
2. Connect device/emulator
3. Click **Run ▶️**

---

## 🔐 Firebase Setup

### Backend:

* Add your Firebase Admin SDK file:

  ```
  backend/serviceAccountKey.json
  ```

### Android:

* Add Firebase config file:

  ```
  luna-android/app/google-services.json
  ```

> ⚠️ These files are not included for security reasons.

---

## 🎯 Innovation

Unlike traditional smart home systems, this project:

* ❌ Does NOT require physical IoT devices
* ✅ Uses **AI + simulation** instead
* 💰 Reduces cost significantly
* ⚙️ Works on any existing home setup

---

## 🧠 How It Works

1. User interacts via **Luna (voice commands)**
2. Commands are sent to **Firebase**
3. Backend processes data using **AI models**
4. Dashboard updates in real-time
5. Energy insights + predictions are generated

---

## 📸 Demo

> Add screenshots or demo video link here

---

## 🏆 Hackathon Value

* Solves real-world energy problems
* Scalable and cost-effective
* Combines AI + Mobile + Cloud
* Easy to deploy and use

---

## 👨‍💻 Author

**Team**
Sky Scraper

---

## ⭐ Future Improvements

* Real IoT device integration
* Mobile dashboard app
* Advanced AI optimization
* Smart automation rules

---
