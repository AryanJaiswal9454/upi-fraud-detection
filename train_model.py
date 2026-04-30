import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (classification_report, confusion_matrix,
                              roc_auc_score, accuracy_score)
from generate_dataset import generate_upi_dataset

def train_models():
    print("📦 Generating dataset...")
    df = generate_upi_dataset(5000)
    df.to_csv('upi_transactions.csv', index=False)

    # Feature engineering
    features = [
        'amount', 'hour_of_day', 'day_of_week', 'transaction_freq_1hr',
        'location_distance_km', 'new_device', 'failed_attempts',
        'account_age_days', 'pin_changed_recently', 'is_weekend'
    ]

    # Encode categoricals
    le_txn = LabelEncoder()
    le_bank = LabelEncoder()
    le_device = LabelEncoder()

    df['txn_type_enc'] = le_txn.fit_transform(df['transaction_type'])
    df['sender_bank_enc'] = le_bank.fit_transform(df['sender_bank'])
    df['device_enc'] = le_device.fit_transform(df['device_type'])

    features += ['txn_type_enc', 'sender_bank_enc', 'device_enc']

    X = df[features]
    y = df['is_fraud']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("🤖 Training models...")

    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_auc = roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1])

    # Gradient Boosting
    gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    gb.fit(X_train, y_train)
    gb_pred = gb.predict(X_test)
    gb_auc = roc_auc_score(y_test, gb.predict_proba(X_test)[:, 1])

    # Logistic Regression
    lr = LogisticRegression(random_state=42, max_iter=1000)
    lr.fit(X_train_scaled, y_train)
    lr_pred = lr.predict(X_test_scaled)
    lr_auc = roc_auc_score(y_test, lr.predict_proba(X_test_scaled)[:, 1])

    print("\n📊 Model Performance:")
    print(f"  Random Forest     → Accuracy: {accuracy_score(y_test, rf_pred)*100:.2f}%  AUC: {rf_auc:.4f}")
    print(f"  Gradient Boosting → Accuracy: {accuracy_score(y_test, gb_pred)*100:.2f}%  AUC: {gb_auc:.4f}")
    print(f"  Logistic Reg      → Accuracy: {accuracy_score(y_test, lr_pred)*100:.2f}%  AUC: {lr_auc:.4f}")

    # Save models
    os.makedirs('models', exist_ok=True)
    with open('models/random_forest.pkl', 'wb') as f:
        pickle.dump(rf, f)
    with open('models/gradient_boosting.pkl', 'wb') as f:
        pickle.dump(gb, f)
    with open('models/logistic_regression.pkl', 'wb') as f:
        pickle.dump(lr, f)
    with open('models/scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    with open('models/label_encoders.pkl', 'wb') as f:
        pickle.dump({'txn_type': le_txn, 'bank': le_bank, 'device': le_device}, f)

    # Save metrics
    metrics = {
        'random_forest': {
            'accuracy': round(accuracy_score(y_test, rf_pred) * 100, 2),
            'auc': round(rf_auc, 4),
            'confusion_matrix': confusion_matrix(y_test, rf_pred).tolist()
        },
        'gradient_boosting': {
            'accuracy': round(accuracy_score(y_test, gb_pred) * 100, 2),
            'auc': round(gb_auc, 4),
            'confusion_matrix': confusion_matrix(y_test, gb_pred).tolist()
        },
        'logistic_regression': {
            'accuracy': round(accuracy_score(y_test, lr_pred) * 100, 2),
            'auc': round(lr_auc, 4),
            'confusion_matrix': confusion_matrix(y_test, lr_pred).tolist()
        },
        'features': features,
        'feature_importance': dict(zip(features, rf.feature_importances_.tolist()))
    }

    import json
    with open('models/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    print("\n✅ Models saved successfully!")
    return metrics

if __name__ == "__main__":
    train_models()
