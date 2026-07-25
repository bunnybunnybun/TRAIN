import requests
import json
import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
script_dir = os.path.dirname(os.path.abspath(__file__))

appID = "9BB16D426AE6D7BB1EDAED215"
routesUrl = f"https://developer.trimet.org/ws/V1/routeConfig?appID={appID}&json=true&dir=true&stops=1"


class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Trimet Bus Tracker")
        self.set_default_size(800, 400)
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

        self.big_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.routesLabel = Gtk.Label(label="Route")
        self.route_dropdown = Gtk.ComboBoxText()
        self.route_dropdown.set_entry_text_column(0)
        self.route_dropdown.connect("changed", self.on_route_selected)

        self.stopsLabel = Gtk.Label(label="Line & Stop")
        self.stop_dropdown = Gtk.ComboBoxText()
        self.stop_dropdown.connect("changed", self.on_stop_selected)

        self.arrivals_explanation_label = Gtk.Label(label="Arrivals")

        self.arrivals_scrolling_window = Gtk.ScrolledWindow()
        self.arrivals_scrolling_window.set_size_request(70, 150)
        self.arrivals_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.arrivals_scrolling_window.add(self.arrivals_box)

        self.left_box.add(self.routesLabel)
        self.left_box.add(self.route_dropdown)
        self.left_box.add(self.stopsLabel)
        self.left_box.add(self.stop_dropdown)
        self.right_box.add(self.arrivals_explanation_label)
        self.right_box.pack_start(self.arrivals_scrolling_window, True, True, 1)
        self.big_box.add(self.left_box)
        self.big_box.pack_start(self.right_box, True, True, 1)

        self.overlay = Gtk.Overlay()
        self.add(self.big_box)

        getRoutes()

        # 2. Start the 30-second loop here
        GLib.timeout_add_seconds(30, self.refresh)

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
        from datetime import datetime, timedelta

        self.last_combo = combo  # 3. Save reference for auto-refresh

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

            current_time_ms = self.arrivalsResponse["resultSet"]["queryTime"]

            # Decide whether to use "estimated" time or "scheduled" time
            if arrival.get("status") == "estimated" and "estimated" in arrival:
                arrival_time_ms = arrival["estimated"]
            else:
                arrival_time_ms = arrival["scheduled"]

            #calculate minutes remaining
            minutes = (arrival_time_ms - current_time_ms) // (1000 * 60)

            #Format raw milliseconds into a readable time
            formatted_time = datetime.fromtimestamp(arrival_time_ms / 1000).strftime("%I:%M %p")

            # Combine time + minutes remaining
            if minutes <= 0:
                time_display_str = f"{formatted_time} | Arriving Now"
            else:
                time_display_str = f"{formatted_time} | {minutes} min"

            # --- Load percentage check ---
            if "loadPercentage" in arrival:
                load_percent = f"{arrival['loadPercentage']}% full"
            else:
                load_percent = "Load percentage is N/A for this bus"

            # --- GTK UI construction ---
            self.individual_arrival_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.individual_arrival_box.get_style_context().add_class("individual_arrival_box")

            self.arrivalShortSign = Gtk.Label(label=f"{short_sign}")
            self.arrivalShortSign.get_style_context().add_class("short_sign")
            self.individual_arrival_box.add(self.arrivalShortSign)
            self.arrivalShortSign.show_all()

            self.arrivalTime = Gtk.Label(label=time_display_str)
            self.arrivalTime.get_style_context().add_class("arrival_time")
            self.individual_arrival_box.add(self.arrivalTime)
            self.arrivalTime.show_all()

            self.arrival_load_percent = Gtk.Label(label=load_percent)
            self.arrival_load_percent.get_style_context().add_class("load_percent")
            self.individual_arrival_box.add(self.arrival_load_percent)
            self.arrival_load_percent.show_all()

            self.arrivals_box.add(self.individual_arrival_box)
            self.arrivals_box.show_all()

# 4. Added refresh method
    def refresh(self):
        if self.last_combo is not None:
            print("Auto-refreshing arrival times...")
            self.on_stop_selected(self.last_combo)
        return True  # Must return True to keep repeating every 30 seconds

win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
