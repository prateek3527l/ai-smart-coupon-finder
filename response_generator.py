def generate_response(best_coupon):
    """
    Generate a conversational chatbot response from coupon data
    Used as fallback when AI is unavailable
    
    Parameters:
    best_coupon (dict): Dictionary containing coupon information
    
    Returns:
    str: Friendly conversational response
    """
    
    # Extract coupon details with safe defaults
    code = best_coupon.get('code', 'SAVE10')
    discount = best_coupon.get('discount', 0)
    rating = best_coupon.get('rating', 0)
    popularity = best_coupon.get('popularity', 0)
    constraints = best_coupon.get('constraints', 'No minimum purchase required')
    # UPDATED: Prefer 'product' field, fallback to 'category'
    product = best_coupon.get('product') or best_coupon.get('category', 'this product')
    website = best_coupon.get('website', 'the store')
    
    # Create rating description
    if rating >= 4.5:
        rating_text = "excellent 🌟"
    elif rating >= 4.0:
        rating_text = "great 👍"
    elif rating >= 3.5:
        rating_text = "good 📝"
    else:
        rating_text = "decent 💫"
    
    # Create popularity description
    if popularity >= 90:
        popular_text = "extremely popular 🔥"
    elif popularity >= 70:
        popular_text = "very popular ⭐"
    elif popularity >= 50:
        popular_text = "trending right now 📈"
    else:
        popular_text = "a hidden gem 💎"
    
    # Build conversational response
    response = f"""🎉 Great news! I found a coupon for you!

✨ Use code **{code}** on {website}

💰 Discount: {discount}%

📌 Conditions:
{constraints}

⭐ Rating: {rating}/5 - {rating_text}
🔥 Popularity: {popularity}% - {popular_text}

🎯 This coupon is a great option based on your search for {product}!

Need help with anything else? Just ask! 😊"""
    
    return response