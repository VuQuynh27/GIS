import json
import math

import pandas as pd
from faker import Faker
from shapely.geometry import Point, Polygon
import random2
from datetime import datetime, timedelta
import osrm

# Define Hanoi bounding box
hanoi_bbox = [105.8422, 21.0024, 105.8669, 21.0222]


# Define function to generate random positions within Hanoi bounding box
def generate_random_position():
    lat = random2.uniform(hanoi_bbox[1], hanoi_bbox[3])
    lon = random2.uniform(hanoi_bbox[0], hanoi_bbox[2])
    return lat, lon


# Define function to generate a sequence of positions for a user within the last 30 minutes
def generate_position_sequence():
    positions = []
    lat, lon = generate_random_position()
    timestamp = datetime.now() - timedelta(minutes=30)
    for i in range(10):
        positions.append({
            'latitude': round(lat, 6),
            'longitude': round(lon, 6),
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
        # Generate a new random position within 100 meters from the previous position
        lat += random2.uniform(-0.0009, 0.0009)
        lon += random2.uniform(-0.0009, 0.0009)
        # Generate a new timestamp with a step of 1 minute
        timestamp += timedelta(minutes=3)
    return positions


# Generate 5 random users with their position sequences within Hanoi bounding box
users = []
for i in range(5):
    user = {
        'id': i + 1,
        'positions': generate_position_sequence()
    }
    users.append(user)

# Create a list of dictionaries to store the user data
user_data = []
for user in users:
    for position in user['positions']:
        user_data.append({
            'user_id': user['id'],
            'latitude': position['latitude'],
            'longitude': position['longitude'],
            'timestamp': position['timestamp']
        })

print(user_data)
# Convert the list of dictionaries to a DataFrame
df = pd.DataFrame(user_data)

# Save the DataFrame to a CSV file
df.to_csv('C:/Users/DELL/OneDrive - Hanoi University of Science and Technology/Desktop/HTTTDL/dataset1.txt', index=False)
