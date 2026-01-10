import numpy as np
from pyproj import Geod

def get_range_and_bearing_vectorized(lat1: float, lon1:float, lat2, lon2):
    # propagae lat1 and lon1 to have the same shape as lat2 and lon2
    lat1 = np.full_like(lat2, lat1)
    lon1 = np.full_like(lon2, lon1)
    breakpoint()
    vec_geod = Geod(ellps="WGS84")
    fwd_az, _back_az, dist_m = vec_geod.inv(lon1, lat1, lon2, lat2)
    return dist_m / 1_000.0, np.deg2rad(fwd_az)

# LAX reference (≈runway 24L/06R midpoint)
lat0, lon0 = 33.9416, -118.4085

# Synthetic trajectory: 20 points, ~30 s apart
lat = np.array([
    33.9416, 33.9417, 33.9419, 33.9422, 33.9426,
    33.9431, 33.9437, 33.9444, 33.9452, 33.9461,
    33.9471, 33.9481, 33.9492, 33.9503, 33.9515,
    33.9527, 33.9539, 33.9551, 33.9563, 33.9575
])

lon = np.array([
   -118.4085, -118.4091, -118.4100, -118.4111, -118.4125,
   -118.4140, -118.4157, -118.4175, -118.4194, -118.4213,
   -118.4229, -118.4243, -118.4255, -118.4264, -118.4270,
   -118.4272, -118.4269, -118.4262, -118.4250, -118.4233
])


get_range_and_bearing_vectorized(
    lat0,
    lon0,
    lat,
    lon
)