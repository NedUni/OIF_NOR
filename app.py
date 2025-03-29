from flask import Flask, jsonify, request
from flask_caching import Cache
from scipy.stats import percentileofscore
import csv
import sys
import re
import os
from datetime import datetime
import pandas as pd
import numpy as np

# Initialise Flask app and cache
app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': "simple"})

# Global variable to hold the DataFrame
df = None

def parse_arguments():
    try:
        date = sys.argv[1]
    except:
        print("Please provide date for file you want to search. Expect DD-MM-YYYY. ")
        sys.exit(1)

    if not re.match(r'^\d{2}-\d{2}-\d{4}$', date):
        print("Date is not in the correct format. Expected DD-MM-YYYY.")
        sys.exit(1)
    try:
        datetime.strptime(date, '%d-%m-%Y')
    except ValueError:
        print("Invalid date provided.")
        sys.exit(1)

    return date

def load_csv_to_dataframe(date):
    csv_file = f"output/{date}.csv"
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' does not exist in the /output directory.")
        exit(1)
    
    try:
        df = pd.read_csv(csv_file)
        # Convert 'cost' column to numeric after removing commas (if it exists)
        if 'cost' in df.columns:
            df['cost'] = df['cost'].astype(str).str.replace(',', '')
            df['cost'] = pd.to_numeric(df['cost'], errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        exit(1)

@app.route("/cheapest", methods=["GET"])
def get_cheapest():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    try:
        sorted_df = df.sort_values(by="cost")
        total_items = len(sorted_df)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_df = sorted_df.iloc[start:end]

        response = {
            'items': paginated_df.to_dict(orient='records'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total_items,
                'total_pages': (total_items + per_page - 1) // per_page
            }
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    stats = {
        'average_price': np.round(df['cost'].mean(), 2),
        'median_price': np.round(df['cost'].median(), 2),
        'total_listings': len(df),
        'price_range': {
            'min': int(df['cost'].min()),
            'max': int(df['cost'].max())
        },
        'average_review_score': np.round(df['review_score'].apply(pd.to_numeric, errors='coerce').mean(), 2) if 'review_score' in df.columns else None,
        'most_common_room_type': df['room_type'].mode()[0] if 'room_type' in df.columns else None
    }
    return jsonify(stats), 200

@app.route("/search", methods=["GET"])
def search_listings():
    keyword = request.args.get('q', '').lower()
    results = df[df.apply(lambda row: keyword in str(row['title']).lower() or keyword in str(row['address']).lower(), axis=1)].to_dict('records')
    return jsonify(results), 200

@app.route("/price_range", methods=["GET"])
def get_price_range():
    min_price = request.args.get('min', type=float)
    max_price = request.args.get('max', type=float)
    filtered_data = df[(df['cost'] >= min_price) & (df['cost'] <= max_price)].to_dict('records')
    return jsonify(filtered_data), 200

@app.route("/best_value", methods=["GET"])
def get_best_value():
    min_price = request.args.get('min', type=float)
    max_price = request.args.get('max', type=float)
    filtered_df = df[(df['cost'] >= min_price) & (df['cost'] <= max_price)]
    
    if 'review_score' in filtered_df.columns:
        filtered_df['review_score'] = pd.to_numeric(filtered_df['review_score'], errors='coerce')
    
    filtered_df = filtered_df.dropna(subset=['review_score', 'cost'])
    filtered_df['value_score'] = filtered_df['review_score'] / filtered_df['cost']
    
    best_value = filtered_df.sort_values('value_score', ascending=False).head(10).to_dict('records')
    return jsonify(best_value), 200

@app.route("/location_analysis", methods=["GET"])
def market_analysis():
    location = request.args.get('location', '', type=str).lower()
    
    if not location:
        return jsonify({"error": "Please provide a location parameter, e.g. ?location=Sydney"}), 400

    filtered_df = df[df['address'].str.lower().str.contains(location, na=False)]
    
    if filtered_df.empty:
        return jsonify({"error": f"No listings found for location '{location}'."}), 404
    
    filtered_df['cost'] = pd.to_numeric(filtered_df['cost'], errors='coerce').fillna(0)
    filtered_df['review_score'] = pd.to_numeric(filtered_df['review_score'], errors='coerce').fillna(0)

    stats = {
        "location": location.title(),
        "total_listings": int(len(filtered_df)),
        "average_price": round(filtered_df['cost'].mean(), 2),
        "median_price": round(filtered_df['cost'].median(), 2),
        "price_variance": round(filtered_df['cost'].var(), 2),
        "min_price": int(filtered_df['cost'].min()),
        "max_price": int(filtered_df['cost'].max()),
        "average_review_score": round(filtered_df['review_score'].mean(), 2) if 'review_score' in filtered_df.columns else None
    }
    
    return jsonify(stats), 200

@app.route("/property_percentile", methods=["GET"])
def property_percentile():
    property_name = request.args.get('name', '', type=str).lower()
    if not property_name:
        return jsonify({"error": "Please provide a property name using the 'name' query parameter."}), 400

    matching_properties = df[df['title'].str.lower().str.contains(property_name, na=False)]
    if matching_properties.empty:
        return jsonify({"error": f"No property found matching '{property_name}'."}), 404

    property_row = matching_properties.iloc[0]
    
    # Assume location is the first part of the address (before a comma)
    address = property_row['address']
    location = address.strip().lower() if address else ''
    
    location_listings = df[df['address'].str.lower().str.contains(location, na=False)]
    if location_listings.empty:
        return jsonify({"error": f"No listings found for location '{location}'."}), 404

    location_listings['cost'] = pd.to_numeric(location_listings['cost'], errors='coerce')
    property_cost = pd.to_numeric(property_row['cost'], errors='coerce')
    if pd.isna(property_cost):
        return jsonify({"error": "The property's cost is not a valid number."}), 500

    costs = location_listings['cost'].tolist()
    percentile = percentileofscore(costs, property_cost)

    result = {
        "property_name": property_row['title'],
        "property_cost": property_cost,
        "location": location.title(),
        "relative_price_percentile": percentile,
        "interpretation": (
            f"This property is in the {percentile:.1f}th percentile of prices in {location.title()}. "
            "A lower percentile indicates it is more affordable relative to its peers."
        )
    }
    return jsonify(result), 200

if __name__ == "__main__":
    # Parse command-line arguments and load the CSV file into a global DataFrame
    date_arg = parse_arguments()
    df = load_csv_to_dataframe(date_arg)

    # Start the Flask app
    app.run(debug=True)