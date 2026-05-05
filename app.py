from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime, timedelta
import glob
import os
from ai_handler import get_ai_response
from logic import recommend_coupons
from response_generator import generate_response

app = Flask(__name__)

# ==============================
# LOAD DATASET - UPDATED (LOAD ALL CSV FILES)
# ==============================
try:
    # Load ALL CSV files in the current directory
    csv_files = glob.glob("*.csv")
    
    if not csv_files:
        raise Exception("No CSV files found in current directory")
    
    print(f"📁 Found {len(csv_files)} CSV files: {csv_files}")
    all_dfs = []
    for file in csv_files:
        df_temp = pd.read_csv(file)
        all_dfs.append(df_temp)
        print(f"✅ Loaded {file}: {len(df_temp)} rows")
    
    # Merge all dataframes
    coupon_df = pd.concat(all_dfs, ignore_index=True)
    print(f"📊 Total combined dataset: {len(coupon_df)} coupons")

    # Ensure required columns exist
    required_columns = ['category', 'discount', 'popularity', 'expiry_days', 'price', 'code', 'website', 'rating']
    for col in required_columns:
        if col not in coupon_df.columns:
            print(f"⚠️ Missing column: {col}")

    # Ensure expiry_days
    if 'expiry_days' not in coupon_df.columns:
        coupon_df['expiry_days'] = 30

    # Create expiry_date
    today = datetime.now()
    coupon_df['expiry_date'] = coupon_df['expiry_days'].apply(
        lambda x: today + timedelta(days=x)
    )

    # Convert numeric
    for col in ['price', 'discount', 'popularity', 'rating', 'expiry_days']:
        coupon_df[col] = pd.to_numeric(coupon_df[col], errors='coerce').fillna(0)

    # NEW: Ensure 'product' column exists for logic.py
    if 'product' not in coupon_df.columns:
        coupon_df['product'] = coupon_df['category']
        print("✓ Created 'product' column from 'category'")

    print("✅ Data cleaned successfully")

except Exception as e:
    print("❌ Error loading dataset:", e)
    coupon_df = pd.DataFrame()

# ==============================
# HOME ROUTE - UPDATED (Website optional)
# ==============================
@app.route('/')
def home():
    if coupon_df.empty:
        return "Dataset not loaded!"

    products = sorted(coupon_df['category'].dropna().unique().tolist())
    websites = sorted(coupon_df['website'].dropna().unique().tolist())
    # NEW: Add "All Websites" option
    websites.insert(0, "All Websites")

    return render_template('index.html', products=products, websites=websites)

# ==============================
# SUGGESTIONS API - NEW ROUTE
# ==============================
@app.route('/suggestions')
def suggestions():
    try:
        if coupon_df.empty:
            return jsonify([])
        
        products = list(set(
            coupon_df['product'].dropna().tolist() +
            coupon_df['category'].dropna().tolist()
        ))
        
        return jsonify(products)
    
    except Exception as e:
        print("❌ Suggestions error:", e)
        return jsonify([])

# ==============================
# CHAT ROUTE - UPDATED
# ==============================
@app.route('/chat', methods=['POST'])
def chat():
    try:
        if coupon_df.empty:
            return jsonify({'success': False, 'error': 'Dataset not loaded'}), 500

        # UPDATED: Only get product from request, ignore website and budget
        product = request.form.get('product', '').strip()
        
        # UPDATED: Force defaults
        budget = 0
        website_param = None

        # UPDATED: Only validate product
        if not product:
            return jsonify({'success': False, 'error': 'Please enter a product name'}), 400

        # ==============================
        # GET RECOMMENDATIONS
        # ==============================
        recommendations = recommend_coupons(coupon_df, product, budget, website_param)

        if recommendations['best_coupon'] is None:
            return jsonify({
                'success': True,
                'chatbot_response': f"No coupons found for {product}",
                'best_coupon': None,
                'top_3_coupons': []
            })

        best = recommendations['best_coupon'].copy()

        # ==============================
        # CALCULATIONS - REMOVED
        # ==============================
        discount = best.get('discount', 0)
        price = best.get('price', 0)
        # final_price and savings removed

        # ==============================
        # DEBUG PRINT
        # ==============================
        print("🔍 DEBUG CHECK:")
        print("BEST:", best)
        print("DISCOUNT:", discount)
        print("PRICE:", price)

        # ==============================
        # AI PROMPT - UPDATED
        # ==============================
        actual_website = best.get('website', 'the store')
        constraints = best.get('constraints', 'No minimum purchase required')

        prompt = f"""
You are a smart coupon assistant.

Product: {product}
Website: {actual_website}

Coupon Details:
Code: {best.get('code')}
Discount: {discount}%
Constraints: {constraints}

Explain why this coupon is useful in 2 sentences.
Mention conditions clearly.
"""

        ai_reply = get_ai_response(prompt)

        # ==============================
        # FALLBACK
        # ==============================
        if not ai_reply:
            chatbot_message = generate_response(best)
        else:
            chatbot_message = ai_reply

        # ==============================
        # RESPONSE JSON - UPDATED (added score and constraints to best_coupon)
        # ==============================
        return jsonify({
            'success': True,
            'chatbot_response': chatbot_message,
            'best_coupon': {
                'code': best.get('code'),
                'discount': float(discount),
                'rating': float(best.get('rating', 0)),
                'popularity': float(best.get('popularity', 0)),
                'website': best.get('website'),
                'product': best.get('category'),
                'score': float(best.get('score', 0)),
                'constraints': best.get('constraints', 'No minimum purchase required')
            },
            'top_3_coupons': [
                {
                    'code': c.get('code'),
                    'discount': float(c.get('discount', 0)),
                    'score': float(c.get('score', 0)),
                    'rating': float(c.get('rating', 0))
                }
                for c in recommendations['top_3_coupons']
            ]
        })

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({'success': False, 'error': 'Server error'}), 500

# ==============================
# RUN APP
# ==============================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
