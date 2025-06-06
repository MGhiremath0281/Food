import streamlit as st
import pandas as pd
import random
from collections import defaultdict
import re
import os

# --- THIS MUST BE THE VERY FIRST STREAMLIT COMMAND ---
st.set_page_config(layout="wide", page_title="Advanced Recipe Recommender", page_icon="🍲")
# ----------------------------------------------------

# --- Configuration and Data Loading ---
script_dir = os.path.dirname(__file__)
DATA_FILE = os.path.join(script_dir, 'recipes.json')

# Add a print statement to verify the path being used
print(f"Attempting to load recipes from: {DATA_FILE}")

@st.cache_data # Cache the data loading for performance
def load_recipes(file_path):
    print(f"Inside load_recipes: Loading {file_path}") # Verify path inside cached function
    try:
        df = pd.read_json(file_path) # Changed to pd.read_json
        # Ingredients are already a list in JSON, so just convert to lowercase
        df['ingredients_list'] = df['ingredients'].apply(lambda x: [item.strip().lower() for item in x])
        return df
    except FileNotFoundError:
        st.error(f"Error: {file_path} not found. Please create the recipes.json file.")
        return pd.DataFrame() # Return empty DataFrame on error
    except Exception as e: # Catch broader exceptions for JSON parsing
        st.error(f"Error parsing JSON file: {e}. Please check your recipes.json file for correct formatting.")
        return pd.DataFrame()

recipes_df = load_recipes(DATA_FILE)

# --- Helper Functions ---
def get_unique_values(df, column):
    if not df.empty:
        return ['Any'] + sorted(df[column].unique().tolist())
    return ['Any']

def recommend_recipes(df, selected_cuisine, selected_meal_type, selected_difficulty,
                      min_prep_time, max_prep_time, min_cook_time, max_cook_time,
                      search_ingredients_str):
    
    filtered_df = df.copy()

    # Apply filters
    if selected_cuisine != 'Any':
        filtered_df = filtered_df[filtered_df['cuisine'] == selected_cuisine]
    if selected_meal_type != 'Any':
        filtered_df = filtered_df[filtered_df['meal_type'] == selected_meal_type]
    if selected_difficulty != 'Any':
        filtered_df = filtered_df[filtered_df['difficulty'] == selected_difficulty]
    
    # Time filters
    filtered_df = filtered_df[
        (filtered_df['prep_time_minutes'] >= min_prep_time) &
        (filtered_df['prep_time_minutes'] <= max_prep_time) &
        (filtered_df['cook_time_minutes'] >= min_cook_time) &
        (filtered_df['cook_time_minutes'] <= max_cook_time)
    ]

    # Ingredient-based search (Advanced matching)
    if search_ingredients_str:
        search_ingredients = [s.strip().lower() for s in search_ingredients_str.split(',') if s.strip()]
        if search_ingredients:
            matched_indices = []
            for index, row in filtered_df.iterrows():
                recipe_ingredients = row['ingredients_list']
                # Check if ALL searched ingredients are present in the recipe's ingredients_list
                if all(any(re.search(r'\b' + re.escape(search_ing) + r'\b', recipe_ing, re.IGNORECASE) for recipe_ing in recipe_ingredients) for search_ing in search_ingredients):
                    matched_indices.append(index)
            filtered_df = filtered_df.loc[matched_indices]

    return filtered_df

def display_recipe(recipe):
    st.subheader(recipe['name'])
    if pd.notna(recipe['image_url']) and recipe['image_url']:
        st.image(recipe['image_url'], width=300)
    st.write(f"**Cuisine:** {recipe['cuisine']}")
    st.write(f"**Meal Type:** {recipe['meal_type']}")
    st.write(f"**Difficulty:** {recipe['difficulty']}")
    st.write(f"**Prep Time:** {recipe['prep_time_minutes']} minutes")
    st.write(f"**Cook Time:** {recipe['cook_time_minutes']} minutes")
    # Display ingredients as a comma-separated string for readability, joining the list
    st.write(f"**Ingredients:** {', '.join(recipe['ingredients'])}")
    with st.expander("View Instructions"):
        st.write(recipe['instructions'])
    st.markdown("---")

# --- Streamlit UI (This section can remain as is) ---

st.title("🍲 Advanced Food Recipe Recommender")

if recipes_df.empty:
    st.warning("No recipes loaded. Please ensure 'recipes.json' exists and is correctly formatted.")
else:
    # Sidebar Filters
    st.sidebar.header("Filter Recipes")

    # Dynamic filters based on data
    cuisines = get_unique_values(recipes_df, 'cuisine')
    meal_types = get_unique_values(recipes_df, 'meal_type')
    difficulties = get_unique_values(recipes_df, 'difficulty')

    selected_cuisine = st.sidebar.selectbox("Cuisine", cuisines)
    selected_meal_type = st.sidebar.selectbox("Meal Type", meal_types)
    selected_difficulty = st.sidebar.selectbox("Difficulty", difficulties)

    st.sidebar.subheader("Time Constraints (minutes)")
    min_prep_time, max_prep_time = st.sidebar.slider(
        "Preparation Time", 0, int(recipes_df['prep_time_minutes'].max() if not recipes_df.empty else 60), 
        (0, int(recipes_df['prep_time_minutes'].max() if not recipes_df.empty else 60))
    )
    min_cook_time, max_cook_time = st.sidebar.slider(
        "Cooking Time", 0, int(recipes_df['cook_time_minutes'].max() if not recipes_df.empty else 90), 
        (0, int(recipes_df['cook_time_minutes'].max() if not recipes_df.empty else 90))
    )

    st.sidebar.markdown("---")
    st.sidebar.header("Ingredient Search")
    search_ingredients_str = st.sidebar.text_input(
        "Ingredients I have (comma-separated):",
        help="e.g., chicken, onion, garlic"
    )

    # Main Content Area
    st.markdown("### Find Your Next Delicious Meal!")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Recommend Recipes"):
            st.session_state['recommended_recipes'] = recommend_recipes(
                recipes_df, selected_cuisine, selected_meal_type, selected_difficulty,
                min_prep_time, max_prep_time, min_cook_time, max_cook_time,
                search_ingredients_str
            )
            st.session_state['display_count'] = 5 # Initial number of recipes to display
            
        if st.button("Surprise Me!"):
            if not recipes_df.empty:
                random_recipe = recipes_df.sample(1).iloc[0]
                st.session_state['recommended_recipes'] = pd.DataFrame([random_recipe])
                st.session_state['display_count'] = 1
            else:
                st.warning("No recipes to surprise you with!")

    with col2:
        if 'recommended_recipes' in st.session_state and not st.session_state['recommended_recipes'].empty:
            st.write(f"Found {len(st.session_state['recommended_recipes'])} matching recipes.")
            
            recipes_to_display = st.session_state['recommended_recipes'].head(st.session_state['display_count'])

            for idx, recipe in recipes_to_display.iterrows():
                display_recipe(recipe)
            
            if len(st.session_state['recommended_recipes']) > st.session_state['display_count']:
                if st.button("Show More Recipes"):
                    st.session_state['display_count'] += 5 # Increase by 5
                    st.experimental_rerun() # Rerun to show more
        elif 'recommended_recipes' in st.session_state:
            st.info("No recipes found matching your criteria. Try adjusting your filters!")