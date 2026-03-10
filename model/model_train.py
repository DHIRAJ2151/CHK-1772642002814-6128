import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = pd.read_csv(r"C:\Users\Welcome\Desktop\krushimitra\krushi_project\Crop_recommendation.csv")

X = data.drop("label", axis=1)
y = data["label"]

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "crop_model.pkl")

print("Model saved successfully")