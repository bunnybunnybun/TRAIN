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
        self.dir_data = []   # Stores direction data for active route
        self.stop_data = []  # Stores stop data for active direction

        def getRoutes():
            self.routesResponse = requests.get(routesUrl).json()
            self.routes_data = self.routesResponse["resultSet"]["route"]

            for route in self.routes_data:
                self.route_dropdown.append_text(route["desc"])

        self.big_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # 1. Route Dropdown
        self.routesLabel = Gtk.Label(label="Route")
        self.route_dropdown = Gtk.ComboBoxText.new_with_entry()
        self.route_dropdown.set_entry_text_column(0)
        self.setup_searchable_combo(self.route_dropdown)
        self.route_dropdown.connect("changed", self.on_route_selected)

        # 2. Direction Dropdown (NEW)
        self.dirLabel = Gtk.Label(label="Direction")
        self.dir_dropdown = Gtk.ComboBoxText()
        self.dir_dropdown.connect("changed", self.on_dir_selected)

        # 3. Stop Dropdown
        self.stopsLabel = Gtk.Label(label="Stop")
        self.stop_dropdown = Gtk.ComboBoxText.new_with_entry()
        self.stop_dropdown.set_entry_text_column(0)
        self.setup_searchable_combo(self.stop_dropdown)
        self.stop_dropdown.connect("changed", self.on_stop_selected)

        self.arrivals_explanation_label = Gtk.Label(label="Arrivals")

        self.arrivals_scrolling_window = Gtk.ScrolledWindow()
        self.arrivals_scrolling_window.set_size_request(70, 150)
        self.arrivals_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.arrivals_scrolling_window.add(self.arrivals_box)

        # Pack all three dropdowns into the left box
        self.left_box.add(self.routesLabel)
        self.left_box.add(self.route_dropdown)
        self.left_box.add(self.dirLabel)
        self.left_box.add(self.dir_dropdown)
        self.left_box.add(self.stopsLabel)
        self.left_box.add(self.stop_dropdown)

        self.right_box.add(self.arrivals_explanation_label)
        self.right_box.pack_start(self.arrivals_scrolling_window, True, True, 1)
        self.big_box.add(self.left_box)
        self.big_box.pack_start(self.right_box, True, True, 1)

        self.add(self.big_box)

        getRoutes()

        # 2. Start the 30-second loop here
        GLib.timeout_add_seconds(30, self.refresh)

    def setup_searchable_combo(self, combo):
        """Attaches interactive auto-completion filtering to a ComboBoxText."""
        entry = combo.get_child()
        completion = Gtk.EntryCompletion()
        completion.set_model(combo.get_model())
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_popup_completion(True)

        def match_func(completion, key, iter, data):
            model = completion.get_model()
            value = model[iter][0]
            return value is not None and key.lower() in value.lower()

        # FIX: When a user clicks or hits Enter on a search match,
        # set the active index on the combo box so "changed" triggers properly!
        def on_match_selected(completion, model, iter):
            path = model.get_path(iter)
            if path:
                combo.set_active(path.get_indices()[0])
            return False  # Let GTK finish inserting the text into the entry

        completion.set_match_func(match_func, None)
        completion.connect("match-selected", on_match_selected)
        entry.set_completion(completion)

    def on_route_selected(self, combo):
        # Clear child dropdowns
        self.dir_dropdown.remove_all()
        self.stop_dropdown.remove_all()
        self.dir_data = []
        self.stop_data = []

        index = combo.get_active()
        if index == -1:
            return

        self.selected_route = self.routes_data[index]
        route_number = self.selected_route["route"]

        print(f"selected route: {route_number}")

        # Populate direction dropdown
        for direction in self.selected_route["dir"]:
            self.dir_dropdown.append_text(direction["desc"])
            self.dir_data.append(direction)

    def on_dir_selected(self, combo):
        # Clear stop dropdown
        self.stop_dropdown.remove_all()
        self.stop_data = []

        index = combo.get_active()
        if index == -1:
            return

        selected_direction = self.dir_data[index]

        # Populate stop dropdown for the chosen direction only
        for stop in selected_direction["stop"]:
            self.stop_dropdown.append_text(stop["desc"])
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

# --- SAFE API REQUEST WITH ERROR HANDLING ---
        try:
            # Added a 5-second timeout so it doesn't hang indefinitely if Wi-Fi drops
            response = requests.get(self.arrivalsUrl, timeout=5)
            response.raise_for_status()
            self.arrivalsResponse = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching arrivals (will retry in 30s): {e}")
            return  # Skip updating the UI this time, but leave the app running!


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
