import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

def create_and_train_dataset():
    np.random.seed(42)
    n_samples = 2500

    catalog_templates = [
        {"id": "SKU-101", "name": "Organic Almond Milk 1L", "category": "Groceries", "base_price": 4.49, "base_cost": 2.20, "base_lead": 3},
        {"id": "SKU-102", "name": "Artisan Sourdough Loaf", "category": "Bakery", "base_price": 5.99, "base_cost": 2.10, "base_lead": 2},
        {"id": "SKU-103", "name": "Premium Colombian Coffee 500g", "category": "Beverages", "base_price": 14.99, "base_cost": 7.80, "base_lead": 5},
        {"id": "SKU-104", "name": "Extra Virgin Olive Oil 750ml", "category": "Pantry", "base_price": 18.50, "base_cost": 10.50, "base_lead": 7},
        {"id": "SKU-105", "name": "Wireless Ergonomic Mouse", "category": "Electronics", "base_price": 29.99, "base_cost": 16.00, "base_lead": 10},
        {"id": "SKU-106", "name": "Eco Bamboo Paper Towels 6pk", "category": "Household", "base_price": 11.49, "base_cost": 5.20, "base_lead": 4},
        {"id": "SKU-107", "name": "Hydrating Facial Cleanser 200ml", "category": "Personal Care", "base_price": 16.99, "base_cost": 6.50, "base_lead": 4},
        {"id": "SKU-108", "name": "Organic Honeycrisp Apples 1kg", "category": "Produce", "base_price": 6.49, "base_cost": 3.10, "base_lead": 2},
        {"id": "SKU-109", "name": "Plant Protein Powder 900g", "category": "Health & Nutrition", "base_price": 34.99, "base_cost": 19.50, "base_lead": 7},
        {"id": "SKU-110", "name": "Dark Chocolate Sea Salt Bark", "category": "Snacks", "base_price": 7.99, "base_cost": 3.40, "base_lead": 3},
    ]

    records = []
    for _ in range(n_samples):
        prod = catalog_templates[np.random.randint(0, len(catalog_templates))]
        
        last_week_sales = int(np.random.uniform(15, 250))
        past_30d_avg = round(float(last_week_sales * np.random.uniform(0.88, 1.12)), 2)
        price_variation = np.random.uniform(0.90, 1.15)
        price = round(float(prod["base_price"] * price_variation), 2)
        cost = round(float(prod["base_cost"]), 2)
        discount_pct = int(np.random.choice([0, 5, 10, 15, 20, 25, 30], p=[0.40, 0.15, 0.15, 0.10, 0.10, 0.05, 0.05]))
        competitor_price = round(float(price * np.random.uniform(0.92, 1.10)), 2)
        lead_time_days = int(np.random.choice([prod["base_lead"], prod["base_lead"] + 1, max(1, prod["base_lead"] - 1)]))
        footfall_factor = round(float(np.random.uniform(0.85, 1.35)), 2)
        current_stock = int(np.random.uniform(5, 350))
        
        effective_price = max(1.0, price * (1.0 - discount_pct / 100.0))
        price_ratio = competitor_price / effective_price
        elasticity_lift = (price_ratio - 1.0) * 0.45
        promo_boost = (discount_pct / 100.0) * 0.65
        base_demand = 0.60 * last_week_sales + 0.40 * past_30d_avg
        predicted_demand = base_demand * (1.0 + elasticity_lift + promo_boost) * footfall_factor
        noise = np.random.normal(0, max(1.0, 0.06 * predicted_demand))
        target_weekly_demand = round(max(5.0, predicted_demand + noise), 1)

        records.append({
            "product_id": prod["id"],
            "product_name": prod["name"],
            "category": prod["category"],
            "current_stock": current_stock,
            "last_week_sales": last_week_sales,
            "past_30d_avg": past_30d_avg,
            "price": price,
            "cost": cost,
            "discount_pct": discount_pct,
            "lead_time_days": lead_time_days,
            "competitor_price": competitor_price,
            "footfall_factor": footfall_factor,
            "target_weekly_demand": target_weekly_demand
        })

    df = pd.DataFrame(records)

    # Save training dataset to CSV in backend
    csv_path = "backend/retail_training_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"Dataset successfully created and saved to: {csv_path} ({len(df)} rows, {len(df.columns)} columns)")

    # Prepare features and target
    feature_cols = [
        "current_stock",
        "last_week_sales",
        "past_30d_avg",
        "price",
        "discount_pct",
        "lead_time_days",
        "competitor_price",
        "footfall_factor"
    ]
    X = df[feature_cols].values
    y = df["target_weekly_demand"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"Model Training Results:")
    print(f" - R^2 Score: {r2:.4f}")
    print(f" - Mean Absolute Error (MAE): {mae:.2f} units")
    print(f" - Root Mean Squared Error (RMSE): {rmse:.2f} units")

    # Persist model
    os.makedirs("models", exist_ok=True)
    model_path = "models/demand_model.joblib"
    joblib.dump(model, model_path)
    print(f"Model saved to: {model_path}")

    # Also save a copy inside backend for convenience
    backend_model_path = "backend/demand_model.joblib"
    joblib.dump(model, backend_model_path)
    print(f"Model copy saved to: {backend_model_path}")

    return model, df

if __name__ == "__main__":
    create_and_train_dataset()
