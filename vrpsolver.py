import pandas as pd
import numpy as np
from pyVRP.src.pyVRP import genetic_algorithm_vrp
import requests
import googlemaps
from gmplot import gmplot
import re
import os

gmaps_api_key='AIzaSyBT_g38I4jmJAQ0NCaS4bDlIY3mMRHQsTI'
class Location:
    def __init__(self,name,lat,lon,l_id,demand):
        self.name=name
        self.lat=lat
        self.lon=lon
        self.l_id=l_id
        self.demand=demand   

def getDistance(loc1,loc2):
    lat1,lon1,lat2,lon2=loc1.lat,loc1.lon,loc2.lat,loc2.lon
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?steps=true"
    # send the request and parse the response
    response = requests.get(url).json()

    # extract the driving distance from the response
    distance = response['routes'][0]['legs'][0]['distance'] / 1000.0  # distance is in meters, convert to kilometers

    # print the driving distance
    return distance

def solveVRP():
    data=pd.read_csv('data.txt',sep='\t')

    yield "Locations fetched"
    locations=[Location(data['Name'][i],data['Latitude'][i],data['Longitude'][i],i,data['Demand'][i]) for i in range(data.shape[0])]

    coordinates=data[['Latitude','Longitude']].values

    # build distance matrix
    distance_matrix=np.arange(len(locations)**2).reshape(len(locations),len(locations))

    yield "Building distance matrix"

    for i in range(len(locations)):
        for j in range(len(locations)):
            distance_matrix[i][j]=getDistance(locations[i],locations[j])
    
    yield "Distance matrix built"
    # build demands matrix
    demands=np.concatenate([data['Demand'].values,np.zeros(len(locations)*4)]).reshape(5,len(locations)).T
    # model parameter setup
    parameters=pd.read_csv('vrp_parameters.txt',sep='\t')

    yield "Setting parameters for GA"
    # Parameters - Model
    n_depots    =  1           # The First n Rows of the 'distance_matrix' or 'coordinates' are Considered as Depots
    time_window = 'without'    # 'with', 'without'
    route       = 'closed'     # 'open', 'closed'
    model       = 'vrp'        # 'tsp', 'mtsp', 'vrp'
    graph       = False        # True, False

    # Parameters - Vehicle
    vehicle_types =   1        # Quantity of Vehicle Types
    fixed_cost    = [0]     # Fixed Cost
    variable_cost = [1]     # Variable Cost 
    capacity      = [parameters['capacity'][0]]     # Capacity of the Vehicle 
    velocity      = [1]     # The Average Velocity Value is Used as a Constant that Divides the Distance Matrix.
    fleet_size    = [parameters['fleet_size'][0]]     # Available Vehicles

    # Parameters - GA
    penalty_value   = parameters['penalty_value'][0]     # GA Target Function Penalty Value for Violating the Problem Constraints
    population_size = parameters['population_size'][0]     # GA Population Size
    mutation_rate   = parameters['mutation_rate'][0]     # GA Mutation Rate
    elite           = parameters['elite'][0]        # GA Elite Member(s) - Total Number of Best Individual(s) that (is)are Maintained 
    generations     = parameters['generations'][0]     # GA Number of Generations
    print(population_size)
    ga_report, ga_vrp = [None], []
    for report in genetic_algorithm_vrp(ga_report, ga_vrp, coordinates, distance_matrix, demands, velocity, fixed_cost, variable_cost, capacity, population_size, vehicle_types, n_depots, route, model, time_window, fleet_size, mutation_rate, elite, generations, penalty_value, graph):
        yield report
    final_routes=ga_vrp[0][1]
    with open("final_routes.txt", "w") as file:
        for route in final_routes:
            file.write(" ".join([str(r) for r in route])+'\n')
    


def plot_driving_route(api_key, locations, output_file):
    colors=['red','yellow','blue','green','purple','pink']
    print(locations)
    # Create the Google Maps client
    client = googlemaps.Client(key=api_key)

    # Create the plot object, centered on the first location
    gmap = gmplot.GoogleMapPlotter(locations[0][0], locations[0][1], 10)

    for i in range(len(locations) - 1):
        # Request directions
        directions_result = client.directions(locations[i], locations[i+1], mode="driving")

        # Get the polyline data from the directions
        polyline = directions_result[0]['overview_polyline']['points']

        # Decode the polyline into latitudes and longitudes
        path = googlemaps.convert.decode_polyline(polyline)

        # Separate the latitudes and longitudes
        latitudes, longitudes = zip(*[(coord['lat'], coord['lng']) for coord in path])

        # Plot the path on the map
        gmap.plot(latitudes, longitudes, colors[i%len(colors)], edge_width=10)

    # Create the HTML map
    gmap.draw(output_file)

    # Read the HTML file
    with open(output_file, "r") as file:
        filedata = file.read()

    # Replace the target string
    filedata = re.sub(f'https://maps.googleapis.com/maps/api/js\?libraries=visualization', 
                      f'https://maps.googleapis.com/maps/api/js?libraries=visualization&sensor=true_or_false&key={api_key}', 
                      filedata)

    # Write the file out again
    with open(output_file, "w") as file:
        file.write(filedata)

def report_routes_info():
    data=pd.read_csv('data.txt',sep='\t')
    locations=[Location(data['Name'][i],data['Latitude'][i],data['Longitude'][i],i,data['Demand'][i]) for i in range(data.shape[0])]
    routes_description=[]
    with open('final_routes.txt','r') as file:
        routes=[[0] + [int(i) for i in line.strip().split()] + [0] for line in file.readlines()]
    for i,route in enumerate(routes):
        plot_driving_route(gmaps_api_key,[[locations[k].lat,locations[k].lon] for k in route],os.path.join(os.path.dirname(__file__), 'templates', 'route_map_'+str(i+1)+'.html'))
        total_distance=0
        total_weight=0
        for j in range(1,len(route)):
            total_distance+=getDistance(locations[route[j-1]],locations[route[j]])
            if j<len(route)-1:
                total_weight+=locations[route[j]].demand
        total_distance=round(total_distance,2)
        routes_description.append("Vehicle = {}, Distance = {}, Weight = {}".format(i+1,total_distance,total_weight))
        print(routes_description[-1])
    return routes_description
        

# report_routes_info()