import os
import joblib
import numpy as np
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Retail Store Optimization API",
    description="ML-driven retail demand forecasting, inventory replenishment, and dynamic pricing optimization platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "demand_model.joblib")
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(os.getcwd(), "models", "demand_model.joblib")

demand_model = None
if os.path.exists(MODEL_PATH):
    try:
        demand_model = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"Warning: Failed loading model from {MODEL_PATH}: {e}")

if demand_model is None:
    from sklearn.ensemble import RandomForestRegressor
    print("Training in-memory fallback model...")
    np.random.seed(42)
    X_dummy = np.random.uniform(5, 200, (600, 8))
    y_dummy = X_dummy[:, 1] * 1.05 + np.random.normal(0, 5, 600)
    demand_model = RandomForestRegressor(n_estimators=50, random_state=42)
    demand_model.fit(X_dummy, y_dummy)

PRODUCTS_DB = [
    {
        "id": "SKU-101",
        "name": "Organic Almond Milk 1L",
        "category": "Groceries",
        "price": 4.49,
        "cost": 2.20,
        "current_stock": 18,
        "last_week_sales": 74,
        "past_30d_avg": 70,
        "lead_time_days": 3,
        "discount_pct": 5,
        "competitor_price": 4.69,
        "shelf_capacity": 120,
        "footfall_factor": 1.15
    },
    {
        "id": "SKU-102",
        "name": "Artisan Sourdough Loaf",
        "category": "Bakery",
        "price": 5.99,
        "cost": 2.10,
        "current_stock": 12,
        "last_week_sales": 95,
        "past_30d_avg": 90,
        "lead_time_days": 2,
        "discount_pct": 0,
        "competitor_price": 5.89,
        "shelf_capacity": 60,
        "footfall_factor": 1.2
    },
    {
        "id": "SKU-103",
        "name": "Premium Ground Colombian Coffee 500g",
        "category": "Beverages",
        "price": 14.99,
        "cost": 7.80,
        "current_stock": 58,
        "last_week_sales": 60,
        "past_30d_avg": 58,
        "lead_time_days": 5,
        "discount_pct": 10,
        "competitor_price": 15.50,
        "shelf_capacity": 100,
        "footfall_factor": 1.1
    },
    {
        "id": "SKU-104",
        "name": "Cold-Pressed Extra Virgin Olive Oil 750ml",
        "category": "Pantry",
        "price": 18.50,
        "cost": 10.50,
        "current_stock": 75,
        "last_week_sales": 38,
        "past_30d_avg": 35,
        "lead_time_days": 7,
        "discount_pct": 0,
        "competitor_price": 19.99,
        "shelf_capacity": 100,
        "footfall_factor": 1.05
    },
    {
        "id": "SKU-105",
        "name": "Wireless Ergonomic Mouse",
        "category": "Electronics",
        "price": 34.99,
        "cost": 16.00,
        "current_stock": 14,
        "last_week_sales": 26,
        "past_30d_avg": 24,
        "lead_time_days": 10,
        "discount_pct": 15,
        "competitor_price": 32.99,
        "shelf_capacity": 40,
        "footfall_factor": 1.0
    },
    {
        "id": "SKU-106",
        "name": "Eco Bamboo Fiber Dish Towels 4-Pack",
        "category": "Household",
        "price": 12.99,
        "cost": 4.50,
        "current_stock": 210,
        "last_week_sales": 18,
        "past_30d_avg": 20,
        "lead_time_days": 7,
        "discount_pct": 0,
        "competitor_price": 11.99,
        "shelf_capacity": 220,
        "footfall_factor": 0.95
    },
    {
        "id": "SKU-107",
        "name": "Hydrating Hyaluronic Facial Serum 50ml",
        "category": "Personal Care",
        "price": 24.50,
        "cost": 9.20,
        "current_stock": 85,
        "last_week_sales": 48,
        "past_30d_avg": 44,
        "lead_time_days": 5,
        "discount_pct": 5,
        "competitor_price": 26.00,
        "shelf_capacity": 100,
        "footfall_factor": 1.15
    },
    {
        "id": "SKU-108",
        "name": "Organic Honeycrisp Apples (3lb Bag)",
        "category": "Produce",
        "price": 6.49,
        "cost": 3.00,
        "current_stock": 140,
        "last_week_sales": 110,
        "past_30d_avg": 105,
        "lead_time_days": 2,
        "discount_pct": 0,
        "competitor_price": 6.99,
        "shelf_capacity": 150,
        "footfall_factor": 1.25
    },
    {
        "id": "SKU-109",
        "name": "Fast-Charging USB-C Cable (2m)",
        "category": "Electronics",
        "price": 11.99,
        "cost": 3.20,
        "current_stock": 90,
        "last_week_sales": 42,
        "past_30d_avg": 40,
        "lead_time_days": 6,
        "discount_pct": 0,
        "competitor_price": 12.50,
        "shelf_capacity": 100,
        "footfall_factor": 1.05
    },
    {
        "id": "SKU-110",
        "name": "Plant-Based Protein Powder 1kg Vanilla",
        "category": "Health & Nutrition",
        "price": 38.99,
        "cost": 21.00,
        "current_stock": 65,
        "last_week_sales": 32,
        "past_30d_avg": 30,
        "lead_time_days": 7,
        "discount_pct": 10,
        "competitor_price": 41.50,
        "shelf_capacity": 80,
        "footfall_factor": 1.05
    }
]

MARKET_BASKET_BUNDLES = [
    {
        "bundle_id": "BNDL-01",
        "name": "Artisan Breakfast Pairing",
        "items": ["Artisan Sourdough Loaf", "Organic Almond Milk 1L", "Premium Ground Colombian Coffee 500g"],
        "confidence": 0.44,
        "lift": 2.38,
        "discount_suggestion": "12% Off Bundle",
        "synergy_score": "High"
    },
    {
        "bundle_id": "BNDL-02",
        "name": "Modern Workspace Setup",
        "items": ["Wireless Ergonomic Mouse", "Fast-Charging USB-C Cable (2m)"],
        "confidence": 0.38,
        "lift": 2.85,
        "discount_suggestion": "15% Off Combined",
        "synergy_score": "Very High"
    },
    {
        "bundle_id": "BNDL-03",
        "name": "Gourmet Mediterranean Kitchen",
        "items": ["Cold-Pressed Extra Virgin Olive Oil 750ml", "Artisan Sourdough Loaf"],
        "confidence": 0.32,
        "lift": 1.95,
        "discount_suggestion": "10% Off Bundle",
        "synergy_score": "Medium"
    },
    {
        "bundle_id": "BNDL-04",
        "name": "Morning Wellness Boost",
        "items": ["Plant-Based Protein Powder 1kg Vanilla", "Organic Almond Milk 1L"],
        "confidence": 0.41,
        "lift": 2.42,
        "discount_suggestion": "10% Off Smoothie Pack",
        "synergy_score": "High"
    }
]

class SingleProductOptimizeRequest(BaseModel):
    product_id: Optional[str] = "CUSTOM"
    name: Optional[str] = "Custom Product"
    current_stock: int = Field(..., ge=0, description="Current stock in units")
    last_week_sales: int = Field(..., ge=0, description="Last 7 days sales")
    past_30d_avg: Optional[int] = None
    price: float = Field(..., gt=0, description="Selling price in USD")
    cost: Optional[float] = None
    discount_pct: float = Field(0.0, ge=0, le=90, description="Active discount %")
    lead_time_days: int = Field(..., ge=1, description="Supplier lead time in days")
    competitor_price: Optional[float] = None
    footfall_factor: float = Field(1.0, ge=0.5, le=2.0, description="Store footfall multiplier")

class OptimizationResult(BaseModel):
    product_id: str
    name: str
    category: Optional[str] = "General"
    current_stock: int
    price: float
    cost: float
    predicted_weekly_demand: int
    predicted_daily_demand: float
    safety_stock: int
    reorder_point: int
    recommended_reorder: int
    estimated_reorder_cost: float
    stockout_probability_pct: float
    days_of_supply: float
    status: str
    status_label: str
    urgency_color: str
    pricing_recommendation: str
    action_notes: str

class PriceSimulationRequest(BaseModel):
    current_price: float
    cost: float
    base_demand: float
    min_price_factor: float = 0.70
    max_price_factor: float = 1.30
    steps: int = 13

def run_optimization_algorithm(item: dict) -> OptimizationResult:
    current_stock = int(item.get("current_stock", 0))
    last_week = float(item.get("last_week_sales", 10))
    past_30 = float(item.get("past_30d_avg") or (last_week * 0.95))
    price = float(item.get("price", 10.0))
    cost = float(item.get("cost") or (price * 0.55))
    discount = float(item.get("discount_pct", 0.0))
    lead_time = int(item.get("lead_time_days", 3))
    comp_price = float(item.get("competitor_price") or price)
    footfall = float(item.get("footfall_factor", 1.0))
    category = str(item.get("category", "General"))
    
    features = np.array([[
        current_stock,
        last_week,
        past_30,
        price,
        discount,
        lead_time,
        comp_price,
        footfall
    ]])
    
    pred_raw = demand_model.predict(features)[0]
    predicted_weekly = max(1, int(round(pred_raw)))
    daily_demand = predicted_weekly / 7.0
    
    lead_time_demand = daily_demand * lead_time
    daily_demand_std = max(1.0, (0.22 * predicted_weekly) / np.sqrt(7.0))
    safety_stock = int(np.ceil(1.65 * np.sqrt(lead_time) * daily_demand_std))
    reorder_point = int(np.ceil(lead_time_demand + safety_stock))
    
    target_inventory = int(np.ceil(reorder_point + (predicted_weekly * 1.2)))
    if current_stock <= reorder_point:
        recommended_reorder = max(0, target_inventory - current_stock)
    else:
        recommended_reorder = 0
        
    estimated_reorder_cost = round(recommended_reorder * cost, 2)
    days_of_supply = round(current_stock / max(0.1, daily_demand), 1)
    
    stock_ratio = current_stock / max(1.0, lead_time_demand)
    stockout_prob = 1.0 / (1.0 + np.exp(2.8 * (stock_ratio - 1.0)))
    stockout_probability_pct = round(float(np.clip(stockout_prob * 100.0, 1.0, 99.0)), 1)
    
    if days_of_supply < lead_time:
        status = "CRITICAL_STOCKOUT"
        status_label = "Critical Stockout Risk"
        urgency_color = "#ef4444"
        action_notes = f"Immediate expedited supplier PO needed. Stock depleted in {days_of_supply} days before lead time ({lead_time}d)."
    elif current_stock <= reorder_point:
        status = "REORDER_NEEDED"
        status_label = "Reorder Required"
        urgency_color = "#f59e0b"
        action_notes = f"Current stock ({current_stock}) crossed ROP ({reorder_point}). Order {recommended_reorder} units to replenish safety buffer."
    elif current_stock > (reorder_point * 2.8) and days_of_supply > 30:
        status = "OVERSTOCKED"
        status_label = "Overstocked"
        urgency_color = "#8b5cf6"
        action_notes = f"Holding {days_of_supply} days of inventory. Consider promotional bundle or 10-15% markdown to unlock working capital."
    else:
        status = "OPTIMAL"
        status_label = "Optimal Health"
        urgency_color = "#10b981"
        action_notes = f"Inventory is well balanced. {days_of_supply} days supply with 95% service level protection."
        
    margin = (price - cost) / max(price, 0.01)
    if comp_price > price * 1.10 and status != "OVERSTOCKED":
        pricing_recommendation = f"Opportunity to increase price to ${round(price * 1.05, 2)} (+5%) while remaining below competitor (${comp_price:.2f})."
    elif status == "OVERSTOCKED":
        pricing_recommendation = f"Recommend temporary {min(20, int(discount + 10))}% promotional discount to accelerate inventory turnover."
    elif comp_price < price * 0.95:
        pricing_recommendation = f"Competitor is pricing lower (${comp_price:.2f}). Monitor price matching or emphasize product bundling."
    else:
        pricing_recommendation = "Current shelf pricing is balanced for steady velocity and healthy margins."

    return OptimizationResult(
        product_id=str(item.get("id", "CUSTOM")),
        name=str(item.get("name", "Custom Item")),
        category=category,
        current_stock=current_stock,
        price=price,
        cost=cost,
        predicted_weekly_demand=predicted_weekly,
        predicted_daily_demand=round(daily_demand, 2),
        safety_stock=safety_stock,
        reorder_point=reorder_point,
        recommended_reorder=recommended_reorder,
        estimated_reorder_cost=estimated_reorder_cost,
        stockout_probability_pct=stockout_probability_pct,
        days_of_supply=days_of_supply,
        status=status,
        status_label=status_label,
        urgency_color=urgency_color,
        pricing_recommendation=pricing_recommendation,
        action_notes=action_notes
    )

@app.get("/api/products")
def get_products():
    return {"status": "success", "count": len(PRODUCTS_DB), "products": PRODUCTS_DB}

@app.post("/api/optimize-single", response_model=OptimizationResult)
def optimize_single(req: SingleProductOptimizeRequest):
    data = req.dict()
    data["id"] = req.product_id
    data["name"] = req.name
    return run_optimization_algorithm(data)

@app.post("/api/optimize-all")
def optimize_all():
    results = [run_optimization_algorithm(p) for p in PRODUCTS_DB]
    total_reorder_units = sum(r.recommended_reorder for r in results)
    total_capital_needed = sum(r.estimated_reorder_cost for r in results)
    critical_count = sum(1 for r in results if r.status == "CRITICAL_STOCKOUT")
    reorder_count = sum(1 for r in results if r.status == "REORDER_NEEDED")
    optimal_count = sum(1 for r in results if r.status == "OPTIMAL")
    overstocked_count = sum(1 for r in results if r.status == "OVERSTOCKED")
    avg_stockout_risk = round(sum(r.stockout_probability_pct for r in results) / len(results), 1)

    return {
        "status": "success",
        "summary": {
            "total_products": len(results),
            "critical_stockouts": critical_count,
            "reorders_needed": reorder_count,
            "optimal_stock": optimal_count,
            "overstocked": overstocked_count,
            "total_recommended_reorder_units": total_reorder_units,
            "total_capital_required_usd": round(total_capital_needed, 2),
            "average_stockout_risk_pct": avg_stockout_risk
        },
        "items": [r.dict() for r in results]
    }

@app.post("/api/simulate-price")
def simulate_price_curve(req: PriceSimulationRequest):
    base_price = req.current_price
    cost = req.cost
    base_demand = req.base_demand
    
    factors = np.linspace(req.min_price_factor, req.max_price_factor, req.steps)
    points = []
    elasticity = -1.65
    best_profit = -1e9
    optimal_price = base_price
    
    for f in factors:
        test_price = round(base_price * f, 2)
        pct_price_change = (test_price - base_price) / max(0.01, base_price)
        pct_demand_change = elasticity * pct_price_change
        
        sim_demand = max(1.0, base_demand * (1.0 + pct_demand_change))
        sim_revenue = round(sim_demand * test_price, 2)
        sim_profit = round(sim_demand * (test_price - cost), 2)
        margin_pct = round(((test_price - cost) / test_price) * 100, 1)
        
        if sim_profit > best_profit:
            best_profit = sim_profit
            optimal_price = test_price
            
        points.append({
            "price": test_price,
            "simulated_weekly_demand": int(round(sim_demand)),
            "simulated_revenue": sim_revenue,
            "simulated_profit": sim_profit,
            "margin_pct": margin_pct,
            "price_delta_pct": round(pct_price_change * 100, 1)
        })
        
    return {
        "status": "success",
        "current_price": base_price,
        "optimal_profit_price": optimal_price,
        "max_estimated_profit": best_profit,
        "curve": points
    }

@app.get("/api/market-basket")
def get_market_basket():
    return {"status": "success", "bundles": MARKET_BASKET_BUNDLES}

@app.get("/api/store-kpis")
def get_store_kpis():
    results = [run_optimization_algorithm(p) for p in PRODUCTS_DB]
    total_skus = len(results)
    at_risk = sum(1 for r in results if r.status in ["CRITICAL_STOCKOUT", "REORDER_NEEDED"])
    healthy = sum(1 for r in results if r.status == "OPTIMAL")
    health_score = int(round((healthy / total_skus) * 100))
    total_reorder_cost = sum(r.estimated_reorder_cost for r in results)
    
    return {
        "health_score_pct": health_score,
        "total_skus": total_skus,
        "skus_needing_action": at_risk,
        "total_replenishment_budget": round(total_reorder_cost, 2),
        "potential_lost_sales_prevented": round(total_reorder_cost * 1.6, 2)
    }

# -------------------------------------------------------------
# Static File & Assets Serving (CSS, JS, HTML Pages)
# -------------------------------------------------------------
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
if os.path.exists(frontend_dir):
    # Explicit routes for style.css and script.js with correct MIME types
    @app.get("/style.css")
    def serve_style_css():
        css_path = os.path.join(frontend_dir, "style.css")
        if os.path.exists(css_path):
            return FileResponse(css_path, media_type="text/css")
        raise HTTPException(status_code=404, detail="style.css not found")

    @app.get("/script.js")
    def serve_script_js():
        js_path = os.path.join(frontend_dir, "script.js")
        if os.path.exists(js_path):
            return FileResponse(js_path, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="script.js not found")

    @app.get("/")
    def serve_root():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Retail Store Optimization API running. Please check frontend/index.html"}

    @app.get("/{page}.html")
    def serve_html_page(page: str):
        page_file = os.path.join(frontend_dir, f"{page}.html")
        if os.path.exists(page_file):
            return FileResponse(page_file)
        raise HTTPException(status_code=404, detail="Page not found")

    # Also mount /static as fallback
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
