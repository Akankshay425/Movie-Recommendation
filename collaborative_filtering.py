import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity


@st.cache_data
def load_movie_data():
    ratings = pd.read_csv("ratings.csv")
    movies = pd.read_csv("movies.csv")

    # Create a user-movie ratings matrix
    user_movie_matrix = ratings.pivot_table(
        index="userId",
        columns="movieId",
        values="rating",
        fill_value=0
    )

    return ratings, movies, user_movie_matrix


@st.cache_data
def calculate_user_similarity():
    _, _, user_movie_matrix = load_movie_data()

    similarities = cosine_similarity(user_movie_matrix)

    similarity_df = pd.DataFrame(
        similarities,
        index=user_movie_matrix.index,
        columns=user_movie_matrix.index
    )

    return similarity_df


def recommend_movies(user_id, top_n=10):
    ratings, movies, user_movie_matrix = load_movie_data()
    similarity_df = calculate_user_similarity()

    if user_id not in user_movie_matrix.index:
        return pd.DataFrame()

    # Find users with similar movie-rating patterns
    similar_users = similarity_df[user_id].drop(user_id)
    similar_users = similar_users[similar_users > 0].sort_values(
        ascending=False
    ).head(50)

    if similar_users.empty:
        return pd.DataFrame()

    # Get movies already rated by the selected user
    user_ratings = user_movie_matrix.loc[user_id]
    unseen_movies = user_ratings[user_ratings == 0].index

    # Predict ratings using the ratings of similar users
    neighbor_ratings = user_movie_matrix.loc[similar_users.index, unseen_movies]

    weighted_scores = neighbor_ratings.mul(
        similar_users, axis=0
    ).sum(axis=0)

    total_similarity = (
        neighbor_ratings.ne(0)
        .mul(similar_users, axis=0)
        .sum(axis=0)
    )

    predicted_ratings = (
        weighted_scores / total_similarity.replace(0, float("nan"))
    ).dropna()

    # Prefer movies with at least 3 ratings from similar users
    rating_counts = neighbor_ratings.ne(0).sum(axis=0)
    predicted_ratings = predicted_ratings[
        rating_counts[predicted_ratings.index] >= 3
    ]

    recommendations = (
        predicted_ratings.sort_values(ascending=False)
        .head(top_n)
        .rename("predicted_rating")
        .reset_index()
    )

    recommendations = recommendations.merge(
        movies, on="movieId", how="left"
    )

    return recommendations