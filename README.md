# Smart Library Book Recommender 📚✨

An intelligent, full-stack book discovery platform that recommends books based on natural-language user queries, educational goals, reading levels, and personal interests.

Built with **Python (Flask)**, **Firebase Authentication & Cloud Firestore**, **Bootstrap 5**, and the official **Google Books API**, driven by a **Python-based weighted TF-IDF similarity recommendation engine**.

---

## 🌟 Key Features

1. **Intelligent Natural-Language Recommendations**
   - Natural language query parser extracts: **Subject**, **Category**, **Reading Level** (Beginner, Intermediate, Advanced, etc.), and **Learning Purpose**.
   - **Multi-Factor Weighted Scoring Algorithm**:
     - 🎯 **Subject Relevance: 35%** (TF-IDF Cosine Similarity on title & topic)
     - 📂 **Category Matching: 25%** (Domain alignment with 14 curated disciplines)
     - ❤️ **User Preference Matching: 20%** (Synced with stored user favourites)
     - 📖 **Reading Level Matching: 10%** (Metadata-backed difficulty detection)
     - 📝 **Description Relevance: 10%** (TF-IDF Cosine Similarity on volume synopsis)
   - Genuine, metadata-backed explanations for every recommendation (*"Recommended because this book matches your interest in Python programming and aligns with your learning category..."*).

2. **Official Google Books API Integration**
   - Live query searching, pagination, sorting, and full detail views.
   - Genuine metadata: Title, Subtitle, Authors, Publisher, Publication Date, ISBN-10, ISBN-13, Page Count, Categories, Ratings, Preview Links.
   - Missing image & description fallbacks with professional SVGs.
   - **Zero fake data generated**.

3. **Modern Split-Screen Authentication**
   - Split-screen visual layout with branded illustrations and book quotes.
   - Firebase Authentication (Email/Password registration & login, password reset, Google sign-in).
   - Category preference selection during registration to seed initial recommendations.
   - Seamless session synchronization between client Firebase tokens and Flask secure backend.

4. **Personalized User Dashboard**
   - Dynamic greetings: *"Welcome back, [Username]!"*
   - Real-time statistics counters:
     - 📌 **Total Saved Books**
     - 📖 **Currently Reading**
     - ✅ **Completed Books**
     - ⏳ **Want to Read**
   - 6 Dynamic Dashboard Sections:
     1. Favourite Categories
     2. Recommended For You (algorithmically scored against user preferences)
     3. Recently Viewed Books
     4. Continue Reading shelf
     5. Recently Saved Books
     6. Recent Search History

5. **My Digital Library**
   - Filter by reading statuses: *All*, *Want to Read*, *Currently Reading*, *Completed*.
   - In-library live title filtering.
   - Change reading status dynamically via dropdown.
   - Duplicate prevention enforced per user.

6. **Ratings & Community Reviews**
   - 1 to 5 Star ratings.
   - Written reviews stored in Cloud Firestore.
   - Aggregate community average rating calculation.
   - Authenticated users can edit or delete their own reviews.

7. **Reading & Search History**
   - Audit trail of previous search queries.
   - Recommendation session logs with thumbnail previews.
   - One-click query replay and history clearing.

8. **Theme & Responsive UI**
   - Dark/Light mode toggle persisted in `localStorage`.
   - Polished color palette: Deep Navy (`#172554`), Royal Blue (`#3B82F6`), Soft Purple (`#8B5CF6`), Clean White/Slate.
   - 100% mobile, tablet, and desktop responsive with Bootstrap 5.

---

## 🏛️ Project Architecture

```
smart_library_book_recommender/
│
├── app.py                         # Application factory & error handlers
├── run.py                         # Development server entry point
├── config.py                      # Environment and app configuration
├── requirements.txt               # Python package dependencies
├── .env.example                   # Sample environment configuration
├── README.md                      # Documentation & setup guide
│
├── services/
│   ├── google_books_service.py    # Official Google Books API integration
│   ├── recommendation_service.py  # NLP query parser & 5-factor weighted TF-IDF engine
│   └── firebase_service.py        # Cloud Firestore CRUD & Admin SDK integration
│
├── routes/
│   ├── auth_routes.py             # Login, register, logout, session sync
│   ├── book_routes.py             # Home page, explore catalog, book details
│   ├── recommendation_routes.py   # AI recommendation processing
│   ├── library_routes.py          # User digital library management
│   ├── review_routes.py           # Ratings & reviews CRUD
│   ├── history_routes.py          # Search & recommendation history
│   └── profile_routes.py          # Dashboard, user profile, category preferences
│
├── templates/
│   ├── base.html                  # Global layout with theme switcher & navbar
│   ├── index.html                 # Landing home with hero & carousels
│   ├── login.html                 # Split-screen sign-in
│   ├── register.html              # Split-screen registration with category picker
│   ├── dashboard.html             # Personalized user dashboard
│   ├── explore.html               # Multi-facet catalog exploration & pagination
│   ├── recommendations.html       # Natural-language AI recommendation interface
│   ├── book_details.html          # Book overview, reviews & related titles
│   ├── my_library.html            # Personal bookshelf & status changer
│   ├── history.html               # Search & session history logs
│   ├── profile.html               # Account settings & stats
│   ├── preferences.html           # 14-discipline preference editor
│   └── 404.html                   # Error fallback page
│
├── static/
│   ├── css/
│   │   ├── style.css              # Main theme design system
│   │   ├── auth.css               # Split-screen auth styles
│   │   ├── dashboard.css          # Metric cards & breakdown badges
│   │   └── responsive.css         # Responsive mobile adjustments
│   ├── js/
│   │   ├── theme.js               # Dark/Light mode switcher
│   │   ├── firebase-config.js     # Web client SDK bootstrap
│   │   ├── auth.js                # Firebase Auth & session sync
│   │   ├── main.js                # Toast dispatcher & navbar effects
│   │   ├── books.js               # Explore live filter & review handling
│   │   ├── recommendations.js     # AI query runner & score breakdown
│   │   └── library.js             # Library CRUD & status updates
│   └── images/
│       ├── logo.svg               # Smart Library vector logo
│       ├── default-book.svg       # Clean SVG cover fallback
│       └── library-illustration.svg # Bookshelf hero illustration
│
└── tests/
    ├── test_books.py              # Google Books API sanitization tests
    └── test_recommendations.py    # NLP & recommendation scoring tests
```

---

## 🚀 Windows Local Setup Instructions

### 1. Prerequisites
- **Python 3.10+** installed on Windows.
- Make sure Python and `pip` are added to your Windows PATH.

### 2. Clone / Navigate to the Project Directory
Open PowerShell or Command Prompt in the project folder:
```powershell
cd "c:\Users\pedda\OneDrive\PROJECTS\Geni AI - Project"
```

### 3. Create a Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` in any text editor. Default development settings are pre-configured so you can run the app immediately.

### 6. Run the Application
```powershell
python run.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔥 Firebase Setup Instructions

To enable full cloud synchronization across multiple devices:

### Step 1: Create a Project in Firebase Console
1. Go to [https://console.firebase.google.com](https://console.firebase.google.com).
2. Click **Add Project** and name it `Smart-Library`.

### Step 2: Enable Firebase Authentication
1. In the left navigation, go to **Build** -> **Authentication**.
2. Click **Get Started**.
3. Under **Sign-in method**, enable **Email/Password**.
4. (Optional) Enable **Google Sign-In**.

### Step 3: Enable Cloud Firestore
1. In the left navigation, go to **Build** -> **Firestore Database**.
2. Click **Create database**.
3. Choose **Start in production mode** (or test mode for 30 days).
4. Select your preferred Cloud Firestore server location.

### Step 4: Get Frontend Web App Credentials
1. In Firebase Console, click the **Settings gear icon (⚙️)** -> **Project settings**.
2. Under **Your apps**, click the **Web icon (</>)**.
3. Register app as `Smart Library Web`.
4. Copy the keys and paste them into your `.env` file:
   ```env
   FIREBASE_API_KEY=AIzaSy...
   FIREBASE_AUTH_DOMAIN=smart-library.firebaseapp.com
   FIREBASE_PROJECT_ID=smart-library
   FIREBASE_STORAGE_BUCKET=smart-library.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=123456789
   FIREBASE_APP_ID=1:123456789:web:abcdef
   ```

### Step 5: Get Firebase Admin SDK Service Account JSON
1. In **Project settings**, go to the **Service accounts** tab.
2. Click **Generate new private key**.
3. Save the downloaded `.json` file in your project root as:
   `firebase-credentials.json`
4. Confirm `FIREBASE_CREDENTIALS_PATH=firebase-credentials.json` in your `.env`.

### Step 6: Firestore Security Rules
In Firebase Console -> Firestore Database -> **Rules**, paste the following security rules:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read and write only their own profile
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    // Users can manage only their own library
    match /user_library/{docId} {
      allow read, write: if request.auth != null && request.resource.data.uid == request.auth.uid;
      allow delete: if request.auth != null && resource.data.uid == request.auth.uid;
    }
    // Users can edit or delete only their own reviews; all users can read reviews
    match /reviews/{reviewId} {
      allow read: if true;
      allow create: if request.auth != null;
      allow update, delete: if request.auth != null && resource.data.uid == request.auth.uid;
    }
    // Private history records
    match /search_history/{docId} {
      allow read, write: if request.auth != null && resource.data.uid == request.auth.uid;
    }
    match /recommendation_history/{docId} {
      allow read, write: if request.auth != null && resource.data.uid == request.auth.uid;
    }
  }
}
```

---

## 🧪 Running Automated Unit Tests

Automated test suites are included to verify Google Books API sanitization and the recommendation algorithm:

```powershell
python -m unittest discover tests
```

You should see all test cases pass:
- `test_books.py`: Volume sanitization, HTTPS enforcement, fallback placeholder handling.
- `test_recommendations.py`: NLP criteria extraction, TF-IDF cosine similarity calculations, 5-weight formula validation, explanation text generator.

---

## 🎓 Final-Year College Project Presentation Guide

When presenting this project to evaluators:

1. **Demonstrate Natural-Language Query Understanding**:
   - Enter *"I want to learn Python programming from beginner to advanced"* in the search box.
   - Point out the **NLP Breakdown** badge showing extracted target subject (*Python Programming*), category (*Programming*), reading level (*Beginner to Advanced*), and purpose (*Learning*).
2. **Explain the Scoring Formula**:
   - Open the **View Score Factors** dropdown on any book card to show the breakdown bars:
     - 35% Subject Relevance
     - 25% Category Match
     - 20% User Preference Alignment
     - 10% Reading Level Fit
     - 10% Description Relevance
3. **Show Real Google Books Data**:
   - Highlight that ISBN numbers, publisher details, Google Books preview links, and page counts are 100% genuine and verified.
4. **Demonstrate Personal Digital Library & Reviews**:
   - Add a book to *Want to Read*, update it to *Currently Reading*, view it on the Personalized Dashboard, and post a 5-star review.
5. **Demonstrate Dark/Light Theme Switching**:
   - Toggle the sun/moon icon in the navbar to show the responsive theme shift.

