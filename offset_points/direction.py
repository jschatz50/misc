#------------#
#-- author --#
#------------#
# Jason Schatz
# Created:  03.31.2017


#----------------------#
#-- file description --#
#----------------------#
# offsets any point along a line by a specified distance in meters
# script first decomposes line path into vertices, figures out which
# line segment the point falls on, and offsets that point by a given 
# distance 90 degrees to the left of the path of the line.


#----------------------#
#-- import libraries --#
#----------------------#
import geopandas as gpd
import geopy
import geopy.distance
from geopy.distance import vincenty
import json
import math
import numpy as np 
import pandas as pd


#----------------------#
#-- define functions --#
#----------------------#
def extract_vertices(geom_path):
	''' extracts vertices from line geometry
	
	Args:
		geom_path: path to geometry file

	Returns:
		list of coordinates as tuples

	'''
	## read file
	gdf = gpd.read_file(geom_path)

	## extract vertices
	vertices = []
	for index, row in gdf.iterrows():
	    for pt in list(row['geometry'].coords): 
	    	vertices.append(pt)
	return vertices

def make_tuples(points):
	track = json.load(open(points))
	vertices = []
	for item in track['features']:
		vertices.append((item['geometry']['coordinates'][0], item['geometry']['coordinates'][1]))
	return vertices

def find_nearest_point(waypoint, vertices):
	''' for a specified waypoint, finds index of nearest point in array of points

	Args:
		waypoint: tuple of coordinates for waypoints
		vertices: list of vertices (tuples of coords)

	Returns:
		index of nearest point in array
	'''
	ver_array = np.array(vertices)
	way_array = np.array(waypoint)

	diff = ver_array - way_array
	dists = np.sqrt(np.sum(diff**2, axis=1))
	min_dist = np.min(dists)
	nearest_point_index = np.where(dists == min_dist)[0][0]

	nearest_point = (ver_array[nearest_point_index][0], ver_array[nearest_point_index][1])
	dist = vincenty(waypoint, nearest_point).meters
	return nearest_point_index, dist

def find_adjacent_points(vertices, nearest_point_index):
	''' return points on either side of the nearest point

	Args:
		vertices: vertices on line
		nearest_point_index: index of nearest vertex on line

	Returns: 
		adjacent points as tuples
	'''
	point1 = vertices[nearest_point_index - 1]
	point2 = vertices[nearest_point_index + 1]
	return point1, point2

def calculate_bearing(point1, point2):
	''' Calculates the bearing between two points

	Args:
		point1: The tuple representing the (lon, lat) for the
		        first point. Latitude and longitude must be in decimal degrees
		point2: The tuple representing the (lon, lat) for the
				second point. Latitude and longitude must be in decimal degrees

	Returns:
		bearing in degrees (float)

	Notes:
		θ = atan2(sin(Δlong).cos(lat2), 
		cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
	'''
	point1 = (point1[1], point1[0])
	point2 = (point2[1], point2[0])

	lat1 = math.radians(point1[0])
	lat2 = math.radians(point2[0])
	diffLong = math.radians(point2[1] - point1[1])
	x = math.sin(diffLong) * math.cos(lat2)
	y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))
	initial_bearing = math.atan2(x, y)

	# normalize the initial bearing
	initial_bearing = math.degrees(initial_bearing)
	compass_bearing = (initial_bearing + 360) % 360
	return compass_bearing

def bearing_to_left(bearing):
	''' Calculates bearing to the left (perpendicular) of initial bearing

	Args:
		bearing: bearing in degrees (float)

	Returns:
		perpendicular bearing in degrees (float)
	'''
	left_bearing = (bearing - 90) % 360
	return left_bearing

def offset_point(waypoint, bearing, distance):
	''' offsets coordinats by specified distance

	Args:
		waypoint: waypoint (tuple of coordinates)
		bearing: bearing in degrees (float)
		distance: offset distance in meters

	Returns:
		perpendicular bearing in degrees (float)
	'''
	initial_point = geopy.Point(waypoint[1], waypoint[0])
	d = geopy.distance.VincentyDistance(meters=distance)
	offsetted = d.destination(point=initial_point, bearing=bearing)
	offsetted = (offsetted[1], offsetted[0])
	return offsetted


#----------------------#
#-- define variables --#
#----------------------#
geom_path = 'F:/Users/Jason/Desktop/working/nodes.geojson'
waypoints = pd.read_csv('F:/Users/Jason/Desktop/working/waypoints.csv')
outpath = 'F:/Users/Jason/Desktop/working/result.csv'   # outpath for offset point coordinates
offset_distance = 15000   # define desired offset in meters


#---------------#
#-- prep data --#
#---------------#
#vertices = extract_vertices(geom_path)
vertices = make_tuples(geom_path)
waypoints = list(zip(waypoints['X'], waypoints['Y']))


#--------------------------#
#-- offset each waypoint --#
#--------------------------#
new_points = []
for waypoint in waypoints:

	## find nearest vertex to the waypoint (and its distance from vertex in meters)
	nearest_point_index, dist = find_nearest_point(waypoint, vertices)
	nearest_vertex = vertices[nearest_point_index]

	## find adjacent vertices (previous and next vertex on line)
	point1, point2 = find_adjacent_points(vertices, nearest_point_index)

	## find bearing to both the previous and next vertex
	bearing_backward = calculate_bearing(point1=point1, 
		                                 point2=waypoint)
	bearing_forward  = calculate_bearing(point1=waypoint,
		                                 point2=point2)

	## figure out which segment the waypoint falls on 
	## to do this, offset a point along each segment & see which is closer to actual waypoint
	back_point = offset_point(nearest_vertex, ((bearing_backward - 180) % 360), distance=dist)   # dist = distance of waypoint from the middle vertex
	forward_point = offset_point(nearest_vertex, bearing_forward, distance=dist)   # dist = distance of waypoint from the middle vertex
	point_list = [back_point, forward_point]
	index1, dist2 = find_nearest_point(waypoint, point_list)

	## select bearing based on which segment the waypoint is on
	bearing_list = [bearing_backward, bearing_forward]
	bearing = bearing_list[index1]
	
	## turn 90 degrees left and offset point by desired amount
	left_bearing = bearing_to_left(bearing)
	offsetted = offset_point(waypoint, left_bearing, distance=offset_distance)
	new_points.append(offsetted)

## write results to file
df = pd.DataFrame(new_points, columns=['X', 'Y'])
df.to_csv(outpath, index=False)
