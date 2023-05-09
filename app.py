from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
import googlemaps
import io
import sys
from contextlib import redirect_stdout
import pandas as pd
import numpy as np
from pyVRP.src.pyVRP import genetic_algorithm_vrp
import requests
from vrpsolver import getDistance,Location,solveVRP,report_routes_info

app = Flask(__name__)
socketio = SocketIO(app)
gmaps = googlemaps.Client(key='AIzaSyBT_g38I4jmJAQ0NCaS4bDlIY3mMRHQsTI')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    num_locations = int(request.form['num_locations'])
    return render_template('form.html', num_locations=num_locations)

@app.route('/save', methods=['POST'])
def save():
    locations = []
    for key, value in request.form.items():
        if key.startswith('location_'):
            idx = int(key.split('_')[-1])
            location_name = value
            demand = request.form[f'demand_{idx}']
            geocode_result = gmaps.geocode(location_name)

            if not geocode_result:
                continue

            lat_lng = geocode_result[0]['geometry']['location']
            locations.append((location_name, lat_lng['lat'], lat_lng['lng'], demand))

    with open('data.txt', 'w') as f:
        f.write('\t'.join(['Name','Latitude','Longitude','Demand']) + '\n')
        for loc in locations:
            f.write('\t'.join(map(str, loc)) + '\n')

    return redirect(url_for('additional_data'))

@app.route('/additional_data')
def additional_data():
    return render_template('additional_data.html')

@app.route('/save_additional_data', methods=['POST'])
def save_additional_data():
    fleet_size = int(request.form['fleet_size'])
    vehicle_capacity = int(request.form['vehicle_capacity'])
    penalty_value = int(request.form.get('penalty_value', 1000))
    population_size = int(request.form.get('population_size', 200))
    mutation_rate = float(request.form.get('mutation_rate', 0.08))
    elite_members = int(request.form.get('elite_members', 1))
    num_generations = int(request.form.get('num_generations', 500))

    additional_data = [
        fleet_size,
        vehicle_capacity,
        penalty_value,
        population_size,
        mutation_rate,
        elite_members,
        num_generations,
    ]

    with open('vrp_parameters.txt', 'w') as f:
        f.write('\t'.join(['fleet_size','capacity','penalty_value','population_size','mutation_rate','elite','generations'])+'\n')
        f.write('\t'.join(map(str, additional_data)) + '\n')

    return redirect(url_for('function_output'))

@app.route('/function_output')
def function_output():
    return render_template('function_output.html')

def my_function():
    # Replace this with the actual function code that prints lines during execution
    for line in solveVRP():
        emit('new_line',{'line': line})
    emit('function_finished')


@socketio.on('start_function', namespace='/function_output')
def handle_start_function():
    my_function()


@app.route('/show_routes')
def show_routes():
    lines = report_routes_info()  # Replace this with a call to your actual function
    return render_template('show_routes.html', lines=lines,N=len(lines))

@app.route("/button/<int:button_number>")
def button_route(button_number):
    # You can use button_number to determine which HTML page to render
    # For this example, let's just render the same HTML page for all buttons
    return render_template('route_map_'+str(button_number)+'.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)
