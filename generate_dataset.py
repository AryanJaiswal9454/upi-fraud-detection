import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

def generate_upi_dataset(n_samples=5000):
    """Generate synthetic UPI transaction dataset"""

    # Transaction types
    txn_types = ['P2P', 'P2M', 'Bill Payment', 'Recharge', 'Shopping']
    banks = ['SBI', 'HDFC', 'ICICI', 'Axis', 'Kotak', 'PNB', 'BOI', 'Canara']
    devices = ['Android', 'iOS', 'Web']

    data = []
    start_date = datetime(2024, 1, 1)

    for i in range(n_samples):
        is_fraud = 1 if random.random() < 0.15 else 0  # 15% fraud rate

        # Amount: fraud txns tend to be high or unusual
        if is_fraud:
            amount = round(random.choice([
                random.uniform(50000, 200000),   # very high amount
                random.uniform(1, 10),            # suspiciously low
                random.uniform(9999, 10001),      # round number boundary
            ]), 2)
        else:
            amount = round(random.uniform(10, 50000), 2)

        # Hour of transaction: fraud more at odd hours
        if is_fraud:
            hour = random.choices(range(24), weights=[
                3,2,2,3,2,1,1,1,2,3,3,3,3,3,3,3,3,3,3,3,3,2,2,3
            ])[0]
        else:
            hour = random.choices(range(24), weights=[
                1,1,1,1,1,1,2,4,6,7,7,7,7,7,7,7,7,7,6,5,4,3,2,1
            ])[0]

        txn_date = start_date + timedelta(
            days=random.randint(0, 365),
            hours=hour,
            minutes=random.randint(0, 59)
        )

        # Number of transactions in last hour (fraud = more)
        txn_freq_1hr = random.randint(5, 20) if is_fraud else random.randint(0, 5)

        # Distance between sender & receiver (fraud = larger)
        location_distance = round(random.uniform(500, 3000), 1) if is_fraud else round(random.uniform(0, 500), 1)

        # Device mismatch (fraud more likely on new device)
        new_device = 1 if (is_fraud and random.random() < 0.7) else (1 if random.random() < 0.1 else 0)

        # Failed attempts before success
        failed_attempts = random.randint(2, 5) if is_fraud else random.randint(0, 1)

        # Account age in days (fraud = newer accounts)
        account_age_days = random.randint(1, 30) if is_fraud else random.randint(30, 3650)

        # UPI PIN change recently
        pin_changed_recently = 1 if (is_fraud and random.random() < 0.6) else (1 if random.random() < 0.05 else 0)

        data.append({
            'transaction_id': f'TXN{i+1:06d}',
            'amount': amount,
            'transaction_type': random.choice(txn_types),
            'sender_bank': random.choice(banks),
            'receiver_bank': random.choice(banks),
            'device_type': random.choice(devices),
            'hour_of_day': hour,
            'day_of_week': txn_date.weekday(),
            'transaction_freq_1hr': txn_freq_1hr,
            'location_distance_km': location_distance,
            'new_device': new_device,
            'failed_attempts': failed_attempts,
            'account_age_days': account_age_days,
            'pin_changed_recently': pin_changed_recently,
            'is_weekend': 1 if txn_date.weekday() >= 5 else 0,
            'timestamp': txn_date.strftime('%Y-%m-%d %H:%M:%S'),
            'is_fraud': is_fraud
        })

    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    df = generate_upi_dataset()
    df.to_csv('upi_transactions.csv', index=False)
    print(f"Dataset generated: {len(df)} records")
    print(f"Fraud cases: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.1f}%)")
