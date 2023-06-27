import csv
import math

import psycopg2
import numpy as np
import pandas as pd
import pyproj as pyproj
from shapely import Polygon, polygonize, Point, LineString, convex_hull
from shapely.wkb import loads
from scipy.spatial import Delaunay, ConvexHull, distance, Voronoi
from shapely.geometry import box
import heapq
from itertools import combinations
from scipy.spatial.distance import euclidean
from geopy.distance import great_circle

conn = psycopg2.connect(
    host="localhost",
    database="osm",
    user="postgres",
    password="quynh27."
)

cur = conn.cursor()
cur.execute("SELECT way FROM planet_osm_point  WHERE amenity = 'restaurant' ")
result = cur.fetchall()
# print(type(result))
P = []
# print("Result Set: ",result)
# Define the source and target coordinate systems
src_crs = 'EPSG:3857'
target_crs = 'EPSG:4326'  # Example: transforming to EPSG 4326 (WGS84)

# Create a transformer object
transformer = pyproj.Transformer.from_crs(src_crs, target_crs, always_xy=True)

# Convert the WKB string to a Shapely geometry object
for i in result:
    wkb_string = bytes.fromhex(i[0])
    geometry = loads(wkb_string)
    # print(geometry)
    # Transform the geometry coordinates
    transformed_geometry = transformer.transform(geometry.x, geometry.y)

    # Extract the transformed coordinates and latitude
    transformed_coordinates = [transformed_geometry[1],
                               transformed_geometry[0]]  # (Longtitude(Kinh do), Latitude (Vi do))
    P.append(transformed_coordinates)

print('Tập P:')
print(P)

# Đọc file csv và lưu vào dataframe
df = pd.read_csv('C:/Users/DELL/OneDrive - Hanoi University of Science and Technology/Desktop/HTTTDL/querypoints.txt')

# Lấy các giá trị latitude và longitude từ dataframe và lưu vào mảng numpy p
Q = np.array(df[['latitude', 'longitude']].values)
print('Tập Q:')
print(Q)
Skyline_points = []


# -------------------------------------

def vs2_algorithm(Q, P):
    # Compute the convex hull of Q
    hull = ConvexHull(Q)
    CH_vertices = Q[hull.vertices]
    print('Bao lồi của tập Q:')
    print(CH_vertices)
    vor = Voronoi(P)
    tri = Delaunay(np.array(P))
    r = np.max([euclidean(p1, p2) for p1, p2 in combinations(Q, 2)])
    # print(r)

    # Initialize S(Q), H, Visited, Extracted, and B
    S = set()
    H = {(tuple(NN(Q[0], P)), mindist(NN(Q[0], P), CH_vertices))}
    # print(H)
    Visited = {tuple(Q[0])}
    Extracted = set()
    B = MBR(SR(NN(Q[0], P), P))
    # print(B)

    # Main loop of the algorithm
    while H:
        # Extract the first entry from H
        H_list = list(H)
        p, key = H_list[0]

        if p in Extracted:
            # If p has already been extracted from H, remove it and continue
            # continue
            H.pop(0)
            # print(p)
            # print(inside_CH(p, CH_vertices))

            # Add p to S if it is inside CH(Q) or not dominated by S
            if inside_CH(p, CH_vertices) or not is_dominated(p, S):
                S.add(tuple(p))
                # print(S)
                B = set(B).intersection(MBR(SR(p, P)))
        else:
            Extracted.add(p)
            if len(S) == 0 or any(tuple(p) in S for p in voronoi_neighbors(p, P, r)):
                # Add the Voronoi neighbors of p to H
                for neighbor in voronoi_neighbors(p, P, r):
                    if tuple(neighbor) in Visited:
                        # If the Voronoi neighbor has already been visited, skip it
                        continue
                    # print(intersects_VC(neighbor, CH_vertices, P))
                    if inside_B(neighbor, B) or intersects_VC(neighbor, CH_vertices, P):
                        # If the Voronoi neighbor is inside B or its V_C intersects B, add it to H
                        Visited.add(tuple(neighbor))
                        dist_to_CH = mindist(neighbor, CH_vertices)
                        neighbor = tuple(neighbor)
                        H = set(H)
                        H.add((neighbor, dist_to_CH))

        # Sort H by the key in each tuple
        H = list(H)
        H.sort(key=lambda x: x[1])
        # print(S)
    return S


def NN(q, P):
    # Find the nearest neighbor of p in Q
    dists = distance.cdist([q], P)
    return P[np.argmin(dists)]


def mindist(p, CH_vertices):
    # Compute the minimum distance from p to CH(Q)
    dists = distance.cdist([p], CH_vertices)
    return np.min(dists)


def MBR(SR):
    # Compute the minimum bounding rectangle (MBR) for a set of circles in SR
    x_min = min([x - r for x, y, r in SR])
    y_min = min([y - r for x, y, r in SR])
    x_max = max([x + r for x, y, r in SR])
    y_max = max([y + r for x, y, r in SR])
    return (x_min, y_min, x_max, y_max)


def SR(p, Q):
    # Compute the set of circles from p to the points in Q
    SR = []
    for q in Q:
        d = distance.euclidean(p, q)
        SR.append((q[0], q[1], d))
    return SR


def inside_B(p, B):
    # Check if a point p is inside the bounding box B
    x_min, y_min, x_max, y_max = B
    return x_min <= p[0] <= x_max and y_min <= p[1] <= y_max


def inside_CH(p, CH_vertices):
    # Check if p lies inside CH(Q)
    # hull = ConvexHull(CH_vertices)
    hull = Delaunay(CH_vertices)
    return hull.find_simplex(p) >= 0


def is_dominated(p, S):
    # Check if p is dominated by any point in S
    for q in S:
        if q[0] <= p[0] and q[1] <= p[1]:
            return True
    return False


def voronoi_neighbors(p, Q, r):
    # Compute the Voronoi neighbors of p from Q
    neighbors = []
    for q in Q:
        if tuple(q) == tuple(p):
            continue
        dist = distance.euclidean(p, q)
        if dist <= r:
            neighbors.append(q)
    return neighbors


def intersects_VC(p, B, P):
    # Check if the Voronoi cell of p intersects with B
    for q in P:
        if tuple(q) == tuple(p):
            continue
        if distance.euclidean(p, q) <= distance.euclidean(p, NN(q, P)):
            if intersects_C(p, q, B):
                return True
    return False

def intersects_C(p, q, B):
    # Count the number of intersections between the circle from p to q and the edges of B
    count = 0
    for i in range(len(B)):
        x1, y1 = B[i]
        x2, y2 = B[(i + 1) % len(B)]
        # Calculate the distance between the center of the circle and the line segment (x1, y1) -> (x2, y2)
        d = abs((y2 - y1) * p[0] - (x2 - x1) * p[1] + x2 * y1 - y2 * x1) / ((y2 - y1)**2 + (x2 - x1)**2)**0.5
        # Check if the line segment intersects with the circle
        if d <= ((q[0] - p[0])**2 + (q[1] - p[1])**2)**0.5 and intersect(p[0], p[1], q[0], q[1], x1, y1, x2, y2):
            count += 1
    # Return True if the number of intersections is odd, False otherwise
    return count % 2 == 1

def intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    # Check if the line segments (x1, y1) -> (x2, y2) and (x3, y3) -> (x4, y4) intersect
    den = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if den == 0:
        return False
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / den
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / den
    if ua >= 0 and ua <= 1 and ub >= 0 and ub <= 1:
        return True
    return False


Skyline_points = vs2_algorithm(Q, P)
print('Số điểm dữ liệu trong tập P:')
print(len(P))
print('Số spatial skyline point:')
print(len(Skyline_points))
print('Spatial skyline points:')
print(Skyline_points)
# --------------------------------
with open("C:/Users/DELL/OneDrive - Hanoi University of Science and Technology/Desktop/HTTTDL/result.txt", 'w',
          newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['latitude', 'longitude'])  # Ghi tiêu đề cho các cột
    for result in Skyline_points:
        writer.writerow([result[0], result[1]])  # Ghi dữ liệu cho mỗi hàng
