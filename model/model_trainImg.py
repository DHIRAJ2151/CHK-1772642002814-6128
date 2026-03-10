import os
import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# --- 1. CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILENAME = 'dataset.csv' 
DATASET_FILE = os.path.join(BASE_DIR, DATASET_FILENAME)

# IMPORTANT: Change 'images' to the actual name of your folder containing the .jpg files
# Based on your folder list, you might need 'static/images' or 'media/images'
IMAGE_FOLDER_NAME = 'images' 
IMAGE_DIR = os.path.join(BASE_DIR, IMAGE_FOLDER_NAME)

MODEL_NAME = 'leaf_model.pkl'
ENCODER_NAME = 'label_encoder.pkl'

def load_and_preprocess_data():
    data = []
    print(f"Reading {DATASET_FILENAME}...")
    
    if not os.path.exists(DATASET_FILE):
        print(f"Error: {DATASET_FILE} not found.")
        return None, None

    with open(DATASET_FILE, 'r') as f:
        lines = f.readlines()
        start_data = False
        count = 0
        
        for line in lines:
            line = line.strip()
            # The file has extra quotes like "@DATA", so we check for DATA
            if 'DATA' in line.upper():
                start_data = True
                continue
            
            if start_data and line:
                # Cleaning the line: "9348.jpg,'Tomato...',?" -> 9348.jpg,'Tomato...',?
                clean_line = line.strip('"') 
                parts = clean_line.split(',')
                
                if len(parts) < 2:
                    continue
                
                # Clean filename and label from any remaining quotes or spaces
                filename = parts[0].strip("'\" ")
                label = parts[1].strip("'\" ")
                
                img_path = os.path.join(IMAGE_DIR, filename)
                
                # Debugging the first image
                if count == 0:
                    print(f"First image search path: {img_path}")
                
                if os.path.exists(img_path):
                    try:
                        img = Image.open(img_path).convert('L') 
                        img = img.resize((64, 64)) 
                        img_data = np.array(img).flatten() / 255.0
                        data.append((img_data, label))
                        count += 1
                    except Exception as e:
                        print(f"Could not process {filename}: {e}")
                
    if not data:
        print(f"\n[!] NO IMAGES FOUND.")
        print(f"The script looked for images in: {IMAGE_DIR}")
        print(f"Please ensure your .jpg files are inside that folder.")
        return None, None
        
    print(f"Successfully loaded {len(data)} images.")
    return zip(*data)

# --- 2. EXECUTION ---
X_raw, y_raw = load_and_preprocess_data()

if X_raw:
    X = np.array(list(X_raw))
    y = np.array(list(y_raw))

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    print("Training model...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)

    accuracy = accuracy_score(y_test, rf.predict(X_test)) * 100
    print(f"Accuracy: {accuracy:.2f}%")

    joblib.dump(rf, MODEL_NAME)
    joblib.dump(label_encoder, ENCODER_NAME)
    print("Files saved successfully.")