# 🎬 Personalized Movie Recommendation System

A machine learning-based movie recommendation system that helps users discover movies based on their interests and ratings from similar users.

## 🚀 Live Demo

[Try the Movie Recommendation App](https://movie-recommendation-48pq3vbbvffmmnweosnoia.streamlit.app/)

## 📌 Project Overview

The Personalized Movie Recommendation System uses collaborative filtering to recommend movies to users based on the preferences of other users with similar rating patterns.

The application provides personalized movie suggestions along with predicted ratings, movie genres, and posters where available.

## ✨ Features

- Personalized movie recommendations
- Collaborative Filtering using user rating patterns
- Cosine Similarity to identify similar users
- Predicted ratings for recommended movies
- Movie posters and genre information
- Interactive web interface built with Streamlit

## 🧠 Machine Learning Approach

**Collaborative Filtering**

The system analyzes user–movie ratings to identify users with similar preferences.

1. Loads movie and rating datasets.
2. Creates a user–movie rating matrix.
3. Calculates user similarity using Cosine Similarity.
4. Identifies similar users.
5. Predicts ratings for movies the selected user has not rated.
6. Recommends movies with the highest predicted ratings.

## 🛠️ Technologies Used

- Python
- Pandas
- NumPy
- Scikit-learn
- Streamlit
- REST API
- TMDB API for movie information and posters, where configured

## 📂 Project Structure

```text
Movie-Recommendation/
├── app.py
├── collaborative_filtering.py
├── movies.csv
├── ratings.csv
├── requirements.txt
└── README.md
```

*Note: The structure above is illustrative. Keep only the filenames that actually exist in your repository.*

## 💻 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/Akankshay425/Movie-Recommendation.git
```

### 2. Open the project directory

```bash
cd Movie-Recommendation
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit application

```bash
streamlit run app.py
```

Make sure the required datasets, dependencies, and API configuration are available before running the application.

## 🎯 Project Objective

The objective of this project is to demonstrate how machine learning techniques can be used to build a personalized movie recommendation system and improve movie discovery through user preference analysis.

## 👩‍💻 Author

**Akanksha Yadav**

[GitHub Profile](https://github.com/Akankshay425)
