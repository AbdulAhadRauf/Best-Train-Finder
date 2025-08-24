# 🚂 Train Ticket Finder

A Streamlit web app to search for Indian Railways train tickets between two stations, check availability, compare fares, and apply smart filters for your journey.

Built by **Abdul Ahad Rauf**.

---

## ✨ Features

* 🔍 Search trains between two stations (source → destination).
* 📅 Choose journey date (with option to include nearby dates).
* 🎟️ Filter by class (1A, 2A, 3A, SL, CC, 3E, etc.).
* ⏰ Filter by preferred departure time (morning, evening, night, etc.).
* ⌛ Set maximum journey duration (hours).
* 📊 Sort trains by **Cheapest** or **Fastest**.
* 💡 Displays key metrics: lowest fare, average fare, highest fare, and fastest journey.
* 🎨 Modern, responsive UI with expandable train cards.

---

## ⚙️ Installation & Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/train-ticket-finder.git
   cd train-ticket-finder
   ```

2. **Create & activate virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / Mac
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:

   ```ini
   USER_ID=your_irctc_user_id
   URL=https://your-api-url-here
   HEADERS={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
   ```

   ⚠️ The app relies on a backend API for fetching train availability. Ensure your headers and API URL are valid.

---

## ▶️ Running the App

Start the Streamlit server:

```bash
streamlit run streamlit_app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📸 Screenshots

*(Add your screenshots here, e.g., UI showing search results, filters, etc.)*

---

## 🛠 Tech Stack

* [Streamlit](https://streamlit.io/) – for frontend & interactivity
* [Pandas](https://pandas.pydata.org/) – for data handling
* [Requests](https://docs.python-requests.org/) – for API calls
* [dotenv](https://pypi.org/project/python-dotenv/) – for environment variables

---

## 📌 Roadmap

* [ ] Add train booking integration
* [ ] Improve alternate train suggestions
* [ ] Deploy to cloud (e.g., Streamlit Cloud / Heroku)
* [ ] Dark mode theme

---

## 📜 License

This project is licensed under the MIT License.

---

👉 Do you also want me to generate a **requirements.txt** file for this app (so installation becomes smoother)?
