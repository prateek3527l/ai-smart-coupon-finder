import pandas as pd
import numpy as np

def clean_data(df):
    """Remove invalid coupons"""
    df = df[df['discount'] > 0]
    df = df[df['price'] > 0]
    df = df[df['price'].notna()]
    return df

def recommend_coupons(df, product, budget, website):
    """
    Recommend coupons based on product, budget, and website
    
    Parameters:
    df (pandas.DataFrame): DataFrame with coupon data
    product (str): Product to search for in product and category columns
    budget (float): Maximum budget/price user is willing to pay
    website (str): Website to filter coupons from (can be None or empty)
    
    Returns:
    dict: Best coupon and top 3 coupons with their scores
    """
    
    # Make a copy to avoid modifying original dataframe
    original_df = df.copy()
    
    # ==================== DATA CLEANING ====================
    # Handle missing values - fill with defaults
    original_df['discount'] = original_df['discount'].fillna(0)
    original_df['popularity'] = original_df['popularity'].fillna(0)
    original_df['rating'] = original_df['rating'].fillna(0)
    original_df['expiry_days'] = original_df['expiry_days'].fillna(30)
    original_df['price'] = original_df['price'].fillna(0)
    
    # Clip values to valid ranges
    original_df['discount'] = original_df['discount'].clip(0, 100)
    original_df['popularity'] = original_df['popularity'].clip(0, 100)
    original_df['rating'] = original_df['rating'].clip(0, 5)
    
    # Convert columns to string for safe searching
    original_df['product'] = original_df['product'].astype(str)
    original_df['category'] = original_df['category'].astype(str)
    original_df['website'] = original_df['website'].astype(str)
    
    # Remove bad coupons
    before_clean = len(original_df)
    original_df = clean_data(original_df)
    print(f"🧹 Removed invalid coupons: {before_clean} → {len(original_df)}")
    
    # Start with a copy for filtering
    filtered_df = original_df.copy()
    
    # ==================== INPUT VALIDATION ====================
    if not product or product.strip() == "":
        print("❌ No product provided")
        return {
            'best_coupon': None,
            'top_3_coupons': [],
            'total_found': 0
        }
    
    # ==================== PRODUCT FILTERING ====================
    product_search = product.strip().lower()
    original_count = len(filtered_df)
    
    # Search in BOTH product and category columns
    try:
        product_mask = filtered_df['product'].str.contains(product_search, case=False, na=False, regex=False)
        category_mask = filtered_df['category'].str.contains(product_search, case=False, na=False, regex=False)
        
        # Try combined search first
        filtered_df = filtered_df[product_mask | category_mask]
        print(f"🔍 Combined search '{product_search}': {len(filtered_df)} coupons (from {original_count})")
        
        # FALLBACK: If no matches, try broader category-only search using original dataframe
        if filtered_df.empty:
            print(f"⚠️ No direct matches, trying broader category search...")
            # Recreate filtered_df from original and create fresh mask
            filtered_df = original_df.copy()
            category_mask = filtered_df['category'].str.contains(product_search, case=False, na=False, regex=False)
            filtered_df = filtered_df[category_mask]
            print(f"📂 Category-only search found: {len(filtered_df)} coupons")
            
            # Re-apply cleaning for fallback results
            if not filtered_df.empty:
                filtered_df = clean_data(filtered_df)
                # Re-convert columns to string after cleaning
                filtered_df['product'] = filtered_df['product'].astype(str)
                filtered_df['category'] = filtered_df['category'].astype(str)
                filtered_df['website'] = filtered_df['website'].astype(str)
            
    except Exception as e:
        print(f"❌ Error in product filtering: {e}")
        return {
            'best_coupon': None,
            'top_3_coupons': [],
            'total_found': 0
        }
    
    # If still no results, return empty
    if filtered_df.empty:
        print("❌ No coupons found matching product criteria")
        return {
            'best_coupon': None,
            'top_3_coupons': [],
            'total_found': 0
        }
    
    # ==================== BUDGET FILTERING ====================
    # UPDATED: Skip budget filtering if budget <= 0
    if budget > 0:
        try:
            budget = float(budget)
            before_budget = len(filtered_df)
            budget_filtered = filtered_df[filtered_df['price'] <= budget]
            
            # Only apply budget filter if it returns results
            if not budget_filtered.empty:
                filtered_df = budget_filtered
                print(f"💰 Budget filter (≤ ₹{budget}): {len(filtered_df)} coupons (from {before_budget})")
            else:
                print(f"⚠️ Budget filter would remove all coupons, skipping budget filter")
        except (ValueError, TypeError):
            print(f"⚠️ Invalid budget value: {budget}, skipping budget filter")
    else:
        print(f"💰 Budget filter skipped (budget = {budget})")
    
    # ==================== WEBSITE FILTERING ====================
    # UPDATED: Skip website filtering if website is None
    if website and isinstance(website, str) and website.strip():
        website_search = website.strip().lower()
        before_website = len(filtered_df)
        try:
            website_filtered = filtered_df[
                filtered_df['website'].str.contains(website_search, case=False, na=False, regex=False)
            ]
            
            # Only apply website filter if it returns results
            if not website_filtered.empty:
                filtered_df = website_filtered
                print(f"🌐 Website filter '{website_search}': {len(filtered_df)} coupons (from {before_website})")
            else:
                print(f"⚠️ Website filter would remove all coupons, skipping website filter")
        except Exception as e:
            print(f"❌ Error in website filtering: {e}")
    else:
        print(f"🌐 No website filter applied (website = {website})")
    
    # ==================== CHECK RESULTS ====================
    if filtered_df.empty:
        print("❌ No coupons found matching criteria")
        return {
            'best_coupon': None,
            'top_3_coupons': [],
            'total_found': 0
        }
    
    # ==================== PREPARE FOR SCORING ====================
    # Ensure expiry_days is at least 1 to prevent division by zero
    filtered_df['expiry_days'] = filtered_df['expiry_days'].apply(lambda x: max(x, 1))
    
    # NORMALIZE VALUES (scale to 0-1 range for fair scoring)
    filtered_df['normalized_discount'] = filtered_df['discount'] / 100.0
    filtered_df['normalized_popularity'] = filtered_df['popularity'] / 100.0
    filtered_df['normalized_rating'] = filtered_df['rating'] / 5.0
    
    # Calculate expiry factor (urgency) - smoothed to avoid extreme values
    # Adding +5 to denominator prevents expiry_days=1 from dominating the score
    filtered_df['expiry_factor'] = 1 / (filtered_df['expiry_days'] + 5)
    
    # ==================== SCORING FORMULA ====================
    # Updated weights: discount 50%, popularity 20%, rating 20%, expiry 10%
    # More realistic for coupon-focused recommendations
    filtered_df['score'] = (
        0.50 * filtered_df['normalized_discount'] +
        0.20 * filtered_df['normalized_popularity'] +
        0.20 * filtered_df['normalized_rating'] +
        0.10 * filtered_df['expiry_factor']
    )
    
    # ==================== ADD HELPER FIELDS ====================
    # Calculate final price and savings
    filtered_df['final_price'] = filtered_df['price'] * (1 - filtered_df['discount'] / 100)
    filtered_df['savings'] = filtered_df['price'] - filtered_df['final_price']
    
    # ==================== SELECT BEST COUPONS ====================
    # Sort by score in descending order (highest first)
    filtered_df = filtered_df.sort_values('score', ascending=False)
    
    # Get best coupon and top 3
    best_coupon = filtered_df.iloc[0].to_dict()
    top_3_coupons = filtered_df.head(3).to_dict('records')
    
    # Debug info
    print(f"✅ Selected best coupon: {best_coupon.get('code', 'N/A')}")
    print(f"   - Discount: {best_coupon.get('discount', 0)}%")
    print(f"   - Price: ₹{best_coupon.get('price', 0):.2f}")
    print(f"   - Final Price: ₹{best_coupon.get('final_price', 0):.2f}")
    print(f"   - Score: {best_coupon.get('score', 0):.3f}")
    print(f"📊 Total matching coupons available: {len(filtered_df)}")
    
    # ==================== RETURN RESULTS ====================
    return {
        'best_coupon': best_coupon,
        'top_3_coupons': top_3_coupons,
        'total_found': len(filtered_df)
    }