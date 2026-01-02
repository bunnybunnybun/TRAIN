import requests
import json
import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
script_dir = os.path.dirname(os.path.abspath(__file__))

appID = "9BB16D426AE6D7BB1EDAED215"
routesUrl = f"https://developer.trimet.org/ws/V1/routeConfig?appID={appID}&json=true&dir=true&stops=1"


class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Trimet Bus Tracker")
        self.set_border_width(20)

        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_path(f"{script_dir}/style.css")
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.routes_data = []

        def getRoutes():
            self.routesResponse = requests.get(routesUrl).json()
            self.routes_data = self.routesResponse["resultSet"]["route"]

            for route in self.routes_data:
                self.route_dropdown.append_text(route["desc"])


        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.routesLabel = Gtk.Label(label="Select route:")
        self.route_dropdown = Gtk.ComboBoxText()
        self.route_dropdown.set_entry_text_column(0)
        self.route_dropdown.connect("changed", self.on_route_selected)

        self.stopsLabel = Gtk.Label(label="Select one of the stops along the route:")
        self.stop_dropdown = Gtk.ComboBoxText()
        self.stop_dropdown.connect("changed", self.on_stop_selected)

        self.arrivals_explanation_label = Gtk.Label(label="Arrivals:")

        self.arrivals_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        self.main_box.add(self.routesLabel)
        self.main_box.add(self.route_dropdown)
        self.main_box.add(self.stopsLabel)
        self.main_box.add(self.stop_dropdown)
        self.main_box.add(self.arrivals_explanation_label)
        self.main_box.add(self.arrivals_box)
        self.add(self.main_box)

        getRoutes()
    
    def on_route_selected(self, combo):
        self.stop_dropdown.remove_all()
        self.stop_data = []

        index = combo.get_active()
        if index == -1:
            return
        
        self.selected_route = self.routes_data[index]
        route_number = self.selected_route["route"]

        print(f"selected route: {route_number}")
        
        for direction in self.selected_route["dir"]:
            direction_name = direction["desc"]

            for stop in direction["stop"]:
                stop_text = f"{direction_name} - {stop['desc']}"
                self.stop_dropdown.append_text(stop_text)
                self.stop_data.append(stop)

    def on_stop_selected(self, combo):
        index = combo.get_active()
        if index == -1:
            return
        
        selected_stop = self.stop_data[index]
        locid = selected_stop["locid"]
        print(f"selected stop locid: {locid}")

        self.arrivalsUrl = f"https://developer.trimet.org/ws/v2/arrivals?appID={appID}&LocIDs={locid}&json=true"
        self.arrivalsResponse = requests.get(self.arrivalsUrl).json()

        arrivals = self.arrivalsResponse["resultSet"]["arrival"]
        self.arrival_info = ""

        # Removing old arrival info
        for child in self.arrivals_box.get_children():
            self.arrivals_box.remove(child)

        for arrival in arrivals:
            route = arrival["route"]
            short_sign = arrival["shortSign"]

            current_time = self.arrivalsResponse["resultSet"]["queryTime"]
            if arrival.get("status") == "estimated" and "estimated" in arrival:
                arrival_time = arrival["estimated"]
            else:
                arrival_time = arrival["scheduled"]
            minutes = (arrival_time - current_time) // (1000 * 60)

            load_percent = arrival["loadPercentage"]

            arrival_info = f"{short_sign} - {minutes} min {load_percent}% full"
            print(arrival_info)

            self.individual_arrival_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.individual_arrival_box.get_style_context().add_class("individual_arrival_box")

            self.arrivalShortSign = Gtk.Label(label=f"{short_sign}")
            self.arrivalShortSign.get_style_context().add_class("short_sign")
            self.individual_arrival_box.add(self.arrivalShortSign)
            self.arrivalShortSign.show_all()

            self.arrivalTime = Gtk.Label(label=f"{minutes} min")
            self.arrivalTime.get_style_context().add_class("arrival_time")
            self.individual_arrival_box.add(self.arrivalTime)
            self.arrivalTime.show_all()

            self.arrival_load_percent = Gtk.Label(label=f"{load_percent}% full")
            self.arrival_load_percent.get_style_context().add_class("load_percent")
            self.individual_arrival_box.add(self.arrival_load_percent)
            self.arrival_load_percent.show_all()

            self.arrivals_box.add(self.individual_arrival_box)
            self.arrivals_box.show_all()
        
win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
