import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# load dataset
data = pd.read_csv("Crop_recommendation.csv")

# features and label
X = data.drop("label", axis=1)
y = data["label"]

# train model
model = RandomForestClassifier()
model.fit(X, y)

# save model
joblib.dump(model, "crop_model.pkl")

print("Model saved successfully")