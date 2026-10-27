import requests
import streamlit as st
from collaborative_filtering import recommend_movies, load_movie_data
# =============================
# CONFIG
# =============================
API_BASE = "https://movie-rec-466x.onrender.com" or "http://127.0.0.1:8000"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")

# =============================
# STYLES (minimal modern)
# =============================
st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
.small-muted { color:#6b7280; font-size: 0.92rem; }
.movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
.card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# STATE + ROUTING (single-file pages)
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"  # home | details
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except:
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)  # short cache for autocomplete
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=25)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1

            tmdb_id = m.get("tmdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")

            with colset[c]:
                if poster:
                    st.image(poster, use_column_width=True)
                else:
                    st.write("🖼️ No poster")

                if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(tmdb_id)

                st.markdown(
                    f"<div class='movie-title'>{title}</div>", unsafe_allow_html=True
                )


def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append(
                {
                    "tmdb_id": tmdb["tmdb_id"],
                    "title": tmdb.get("title") or x.get("title") or "Untitled",
                    "poster_url": tmdb.get("poster_url"),
                }
            )
    return cards


# =============================
# IMPORTANT: Robust TMDB search parsing
# Supports BOTH API shapes:
# 1) raw TMDB: {"results":[{id,title,poster_path,...}]}
# 2) list cards: [{tmdb_id,title,poster_url,...}]
# =============================
def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    """
    Returns:
      suggestions: list[(label, tmdb_id)]
      cards: list[{tmdb_id,title,poster_url}]
    """
    keyword_l = keyword.strip().lower()

    # A) If API returns dict with 'results'
    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                    "release_date": m.get("release_date", ""),
                }
            )

    # B) If API returns already as list
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            # might be {tmdb_id,title,poster_url}
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": poster_url,
                    "release_date": m.get("release_date", ""),
                }
            )
    else:
        return [], []

    # Word-match filtering (contains)
    matched = [x for x in raw_items if keyword_l in x["title"].lower()]

    # If nothing matched, fallback to raw list (so never blank)
    final_list = matched if matched else raw_items

    # Suggestions = top 10 labels
    suggestions = []
    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    # Cards = top N
    cards = [
        {"tmdb_id": x["tmdb_id"], "title": x["title"], "poster_url": x["poster_url"]}
        for x in final_list[:limit]
    ]
    return suggestions, cards


# =============================
# SIDEBAR (clean)
# =============================
with st.sidebar:
    st.markdown("## 🎬 Menu")
    if st.button("🏠 Home"):
        goto_home()

    st.markdown("---")
    st.markdown("### 🏠 Home Feed (only home)")
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
    )
    grid_cols = st.slider("Grid columns", 4, 8, 6)

    # Personalized recommendations: store favorite movie titles in this browser session
    if "favorite_movies" not in st.session_state:
        st.session_state.favorite_movies = []

    st.markdown("---")
    st.markdown("### ❤️ Personalize Your Feed")
    favorite_query = st.text_input(
        "Add a favourite movie",
        placeholder="e.g. Interstellar",
        key="favorite_query",
    )
    favorite_options = []
    if len(favorite_query.strip()) >= 2:
        fav_data, fav_err = api_get_json(
            "/tmdb/search", params={"query": favorite_query.strip()}
        )
        if not fav_err and fav_data:
            favorite_options, _ = parse_tmdb_search_to_cards(
                fav_data, favorite_query.strip(), limit=10
            )

    if favorite_options:
        favorite_labels = [item[0] for item in favorite_options]
        chosen_favorite = st.selectbox(
            "Choose your movie", favorite_labels, key="favorite_choice"
        )
        if st.button("➕ Add to favourites", use_container_width=True):
            chosen_id = dict(favorite_options)[chosen_favorite]
            if not any(m["tmdb_id"] == chosen_id for m in st.session_state.favorite_movies):
                st.session_state.favorite_movies.append(
                    {"tmdb_id": chosen_id, "title": chosen_favorite.rsplit(" (", 1)[0]}
                )
            st.rerun()

    if st.session_state.favorite_movies:
        st.caption("Your favourites:")
        for fav in st.session_state.favorite_movies:
            st.write("❤️ " + fav["title"])
        remove_title = st.selectbox(
            "Remove a favourite (optional)",
            [m["title"] for m in st.session_state.favorite_movies],
            key="remove_favorite_choice",
        )
        if st.button("➖ Remove selected", use_container_width=True):
            st.session_state.favorite_movies = [
                m for m in st.session_state.favorite_movies if m["title"] != remove_title
            ]
            st.rerun()

# =============================
# HEADER
# =============================
st.title("🎬 Movie Recommender")
st.markdown(
    "<div class='small-muted'>Type keyword → dropdown suggestions + matching results → open → details + recommendations</div>",
    unsafe_allow_html=True,
)
st.divider()

# ==========================================================
# VIEW: HOME
# ==========================================================
if st.session_state.view == "home":
    typed = st.text_input(
        "Search by movie title (keyword)", placeholder="Type: avenger, batman, love..."
    )

    st.divider()

    # SEARCH MODE (Autocomplete + word-match results)
    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters for suggestions.")
        else:
            data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"Search failed: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(
                    data, typed.strip(), limit=24
                )

                # Dropdown
                if suggestions:
                    labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
                    selected = st.selectbox("Suggestions", labels, index=0)

                    if selected != "-- Select a movie --":
                        # map label -> id
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try another keyword.")

                st.markdown("### Results")
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")

        st.stop()

# ==========================================================
    # HOME FEED MODE
    # ==========================================================
    st.markdown(f"### 🏠 Home — {home_category.replace('_', ' ').title()}")

    home_cards, err = api_get_json(
        "/home", params={"category": home_category, "limit": 24}
    )

    if err or not home_cards:
        st.error(f"Home feed failed: {err or 'Unknown error'}")
        st.stop()

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

    # ==========================================================
    # PERSONALIZED RECOMMENDATIONS
    # ==========================================================
    if st.session_state.get("favorite_movies"):
        st.divider()
        st.markdown("## 🎯 Recommended For You")
        st.caption(
            "Based on your favourite movies. Add more favourites "
            "in the sidebar to refine these suggestions."
        )

        personalized_cards = []
        seen_ids = set(
            m["tmdb_id"] for m in st.session_state.favorite_movies
        )

        for favorite in st.session_state.favorite_movies[:3]:
            bundle, rec_err = api_get_json(
                "/movie/search",
                params={
                    "query": favorite["title"],
                    "tfidf_top_n": 8,
                    "genre_limit": 1,
                },
            )

            if not rec_err and bundle:
                for item in bundle.get("tfidf_recommendations", []):
                    movie = item.get("tmdb") or {}
                    movie_id = movie.get("tmdb_id")

                    if movie_id and movie_id not in seen_ids:
                        seen_ids.add(movie_id)
                        personalized_cards.append(
                            {
                                "tmdb_id": movie_id,
                                "title": (
                                    movie.get("title")
                                    or item.get("title")
                                    or "Untitled"
                                ),
                                "poster_url": movie.get("poster_url"),
                            }
                        )

        if personalized_cards:
            poster_grid(
                personalized_cards[:18],
                cols=grid_cols,
                key_prefix="personalized",
            )
        else:
            st.info(
                "Recommendations are not available for these favourites yet. "
                "Try adding a different movie."
            )

    # ==========================================================
    # COLLABORATIVE FILTERING
    # ==========================================================
    st.divider()
    st.markdown("## 🤝 Collaborative Filtering")
    st.caption(
        "Discover movies based on ratings from users with similar tastes."
    )

    try:
        _, _, user_movie_matrix = load_movie_data()
        user_ids = sorted(user_movie_matrix.index.tolist())

        if not user_ids:
            st.info("No users found in the ratings dataset.")
        else:
            selected_user = st.selectbox(
                "Select a MovieLens user",
                user_ids,
                key="cf_user_select",
            )

            if st.button("✨ Get Recommendations", key="cf_button"):
                with st.spinner("Finding movies you may like..."):
                    recommendations = recommend_movies(
                        int(selected_user),
                        top_n=10,
                    )

                if not recommendations.empty:
                    st.markdown(
                        f"### 🎯 Recommended movies for User {selected_user}"
                    )

                    for _, movie in recommendations.iterrows():
                        st.write(
                            f"🎬 **{movie['title']}** — "
                            f"Predicted rating: "
                            f"{movie['predicted_rating']:.2f}/5"
                        )
                else:
                    st.info(
                        "No recommendations found. Try another user."
                    )

    except Exception as e:
        st.error(f"Collaborative Filtering error: {e}")


# ==========================================================
# VIEW: DETAILS
# ==========================================================

elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.warning("No movie selected.")
        if st.button("← Back to Home"):
            goto_home()
        st.stop()

    # Top bar
    a, b = st.columns([3, 1])
    with a:
        st.markdown("### 📄 Movie Details")
    with b:
        if st.button("← Back to Home"):
            goto_home()

    # Details (your FastAPI safe route)
    data, err = api_get_json(f"/movie/id/{tmdb_id}")
    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        st.stop()

    # Layout: Poster LEFT, Details RIGHT
    left, right = st.columns([1, 2.4], gap="large")

    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if data.get("poster_url"):
            st.image(data["poster_url"], use_column_width=True)
        else:
            st.write("🖼️ No poster")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"## {data.get('title','')}")
        release = data.get("release_date") or "-"
        genres = ", ".join([g["name"] for g in data.get("genres", [])]) or "-"
        st.markdown(
            f"<div class='small-muted'>Release: {release}</div>", unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='small-muted'>Genres: {genres}</div>", unsafe_allow_html=True
        )
        st.markdown("---")
        st.markdown("### Overview")
        st.write(data.get("overview") or "No overview available.")
        st.markdown("</div>", unsafe_allow_html=True)

    if data.get("backdrop_url"):
        st.markdown("#### Backdrop")
        st.image(data["backdrop_url"], use_column_width=True)

    st.divider()
    st.markdown("### ✅ Recommendations")

    # Recommendations (TF-IDF + Genre) via your bundle endpoint
    title = (data.get("title") or "").strip()
    if title:
        bundle, err2 = api_get_json(
            "/movie/search",
            params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
        )

        if not err2 and bundle:
            st.markdown("#### 🔎 Similar Movies (TF-IDF)")
            poster_grid(
                to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
                cols=grid_cols,
                key_prefix="details_tfidf",
            )

            st.markdown("#### 🎭 More Like This (Genre)")
            poster_grid(
                bundle.get("genre_recommendations", []),
                cols=grid_cols,
                key_prefix="details_genre",
            )
        else:
            st.info("Showing Genre recommendations (fallback).")
            genre_only, err3 = api_get_json(
                "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
            )
            if not err3 and genre_only:
                poster_grid(
                    genre_only, cols=grid_cols, key_prefix="details_genre_fallback"
                )
            else:
                st.warning("No recommendations available right now.")
    else:
        st.warning("No title available to compute recommendations.")