from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# Dummy training data
X_train = [[0, 0], [1, 1]]
y_train = [0, 1]

model = RandomForestClassifier()
model.fit(X_train, y_train)

# Save the model in the krushi app folder
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
joblib.dump(model, MODEL_PATH)

print(f"Model saved at {MODEL_PATH}")