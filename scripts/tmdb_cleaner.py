import os
import time
import pandas as pd
import requests

# ==============================================================================
# ⚙️ GLOBAL CONFIGURATIONS & SECURITY GOVERNANCE
# ==============================================================================
BASE_URL = 'https://api.themoviedb.org/3'

# 🌟 Security Standard: Fetch API Key from environment variables to avoid credential leakage
API_KEY = os.getenv('TMDB_API_KEY')

if not API_KEY:
    raise ValueError(
        "❌ Error: Environment variable 'TMDB_API_KEY' not found.\n"
        "Please set the environment variable before running the script:\n"
        "Windows (CMD): set TMDB_API_KEY=your_key_here\n"
        "Mac/Linux: export TMDB_API_KEY=\"your_key_here\""
    )

# ==============================================================================
# 🚀 CORE METADATA ENRICHMENT FUNCTIONS
# ==============================================================================
def get_details_by_id(tmdb_id):
    """
    Dynamically requests the TV/Movie endpoints via TMDB_ID to fetch standardized 
    English categorical tags (Genres). Implements a multi-endpoint fallback mechanism.
    """
    try:
        # Standardize ID format to eliminate potential float-to-string anomalies (.0)
        clean_id = int(float(tmdb_id))
        
        # Priority 1: Attempt lookup via the TV Series endpoint
        tv_url = f"{BASE_URL}/tv/{clean_id}"
        params = {'api_key': API_KEY, 'language': 'en-US'}
        
        response = requests.get(tv_url, params=params, timeout=10)
        res_data = response.json()
        
        # Fallback Mechanism: If not matched in TV, attempt lookup via the Movie endpoint
        if 'name' not in res_data:
            movie_url = f"{BASE_URL}/movie/{clean_id}"
            response = requests.get(movie_url, params=params, timeout=10)
            res_data = response.json()
        
        # Parse and join genre tags from metadata payload
        genres = [g['name'] for g in res_data.get('genres', [])]
        return ", ".join(genres) if genres else None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Request Exception [ID: {tmdb_id}]: {e}")
        return None
    except (ValueError, TypeError) as e:
        print(f"❌ Data Transformation Exception [ID: {tmdb_id}]: {e}")
        return None

# ==============================================================================
# 🔄 ETL DATA PIPELINE EXECUTION (FALLBACK & GOVERNANCE MODE)
# ==============================================================================
def main():
    # Use relative paths instead of absolute local paths to maximize project portability
    input_path = 'data/Drama_Full_Enriched_v2.csv'
    output_path = 'data/Drama_Final_Perfect.csv'
    
    if not os.path.exists(input_path):
        print(f"⚠️ Execution Aborted: Input file not found at {input_path}. Check your repository structure.")
        return

    df = pd.read_csv(input_path)
    print("🔍 Initializing Data Quality Fallback Pipeline... Scanning for missing attributes...")
    
    success_count = 0

    for index, row in df.iterrows():
        # Case A: Valid ID exists, but Genres field is missing, empty, or pending
        has_id = pd.notna(row['TMDB_ID'])
        genre_val = str(row.get('Genres_EN', '')).strip()
        is_genre_dirty = pd.isna(row['Genres_EN']) or genre_val in ["", "Pending API Detail"]
        
        if has_id and is_genre_dirty:
            new_genre = get_details_by_id(row['TMDB_ID'])
            if new_genre:
                df.at[index, 'Genres_EN'] = new_genre
                success_count += 1
                print(f"✨ Successfully Enriched Genres: {row['Title_ZH']} -> {new_genre}")
                
            # API Friendly Mechanism: Throttling requests to prevent rate-limiting (429)
            time.sleep(0.1)

        # Case B: Long-tail data anomaly where even the English Title failed to map
        elif pd.isna(row['Title_EN']) or str(row.get('Title_EN', '')).strip() == "":
            print(f"⚠️ Data Governance Warning (Omission): Unmapped official metadata for title: {row['Title_ZH']}")

    # Ensure target output directory exists prior to writing
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Export cleaned and enriched final Fact Table
    df.to_csv(output_path, index=False)
    print(f"\n🎯 Pipeline Completed Successfully! Repaired {success_count} missing records.")
    print(f"💾 Cleaned Fact Table exported to: {output_path}")

if __name__ == "__main__":
    main()