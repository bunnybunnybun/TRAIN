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
        self.dir_data = []   # Direction data
        self.stop_data = []  # Stop data for active direction

        def getRoutes():
            self.routesResponse = requests.get(routesUrl).json()
            self.routes_data = self.routesResponse["resultSet"]["route"]

            for route in self.routes_data:
                self.route_dropdown.append_text(route["desc"])

        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # MenuButton & Popover Container
        self.menu_button = Gtk.MenuButton()
        self.menu_button.get_style_context().add_class("main_select_button")
        self.menu_button.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        self.menu_button.set_halign(Gtk.Align.START)
        self.menu_button.set_valign(Gtk.Align.CENTER)

        self.popover = Gtk.Popover()
        self.popover.set_transitions_enabled(False)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self.menu_button.set_popover(self.popover)

        self.top_bar.pack_start(self.menu_button, False, False, 0)

        # Controls box inside Popover
        self.controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.controls_box.set_border_width(12)

        # Route Dropdown
        self.routesLabel = Gtk.Label(label="Route")
        self.route_dropdown = Gtk.ComboBoxText.new_with_entry()
        self.route_dropdown.set_entry_text_column(0)
        self.setup_searchable_combo(self.route_dropdown)
        self.route_dropdown.connect("changed", self.on_route_selected)

        # Direction Dropdown
        self.dirLabel = Gtk.Label(label="Direction")
        self.dir_dropdown = Gtk.ComboBoxText()
        self.dir_dropdown.connect("changed", self.on_dir_selected)

        # Stop Dropdown
        self.stopsLabel = Gtk.Label(label="Stop")
        self.stop_dropdown = Gtk.ComboBoxText.new_with_entry()
        self.stop_dropdown.set_entry_text_column(0)
        self.setup_searchable_combo(self.stop_dropdown)
        self.stop_dropdown.connect("changed", self.on_stop_selected)


        self.controls_box.add(self.routesLabel)
        self.controls_box.add(self.route_dropdown)
        self.controls_box.add(self.dirLabel)
        self.controls_box.add(self.dir_dropdown)
        self.controls_box.add(self.stopsLabel)
        self.controls_box.add(self.stop_dropdown)

        self.popover.add(self.controls_box)

        self.controls_box.show_all()

        self.center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.center_box.set_halign(Gtk.Align.CENTER)

        self.arrivals_explanation_label = Gtk.Label(label="Arrivals")
        self.arrivals_explanation_label.get_style_context().add_class("arrivals_header")

        self.arrivals_scrolling_window = Gtk.ScrolledWindow()
        self.arrivals_scrolling_window.set_size_request(400, 150)
        self.arrivals_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.arrivals_scrolling_window.add(self.arrivals_box)

        self.center_box.add(self.arrivals_explanation_label)
        self.center_box.pack_start(self.arrivals_scrolling_window, True, True, 0)

        self.main_vbox.pack_start(self.top_bar, False, False, 0)
        self.main_vbox.pack_start(self.center_box, True, True, 0)

        self.add(self.main_vbox)

        getRoutes()

        GLib.timeout_add_seconds(30, self.refresh)

    def setup_searchable_combo(self, combo):
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

        def on_match_selected(completion, model, iter):
            path = model.get_path(iter)
            if path:
                combo.set_active(path.get_indices()[0])
            return False

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

        # Populate stop dropdown for chosen direction
        for stop in selected_direction["stop"]:
            self.stop_dropdown.append_text(stop["desc"])
            self.stop_data.append(stop)

    def on_stop_selected(self, combo):
        from datetime import datetime, timedelta

        self.last_combo = combo

        index = combo.get_active()
        if index == -1:
            return

        selected_stop = self.stop_data[index]
        locid = selected_stop["locid"]
        print(f"selected stop locid: {locid}")

        self.arrivalsUrl = f"https://developer.trimet.org/ws/v2/arrivals?appID={appID}&LocIDs={locid}&json=true"

        try: #Fixed app crashing when loss of wifi
            response = requests.get(self.arrivalsUrl, timeout=5)
            response.raise_for_status()
            self.arrivalsResponse = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching arrivals (will retry in 30s): {e}")
            return


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

            #format scheduled time
            scheduled_time_ms = arrival.get("scheduled")
            if scheduled_time_ms:
                scheduled_formatted = datetime.fromtimestamp(scheduled_time_ms / 1000).strftime("%I:%M %p")
                #calculate if arrival time is late, early, or on time.
                minutes_dif = (arrival_time_ms - scheduled_time_ms) // (1000 * 60)
                #
                on_time = True
                if minutes_dif < 0:
                    time_dif_display_str = f"{minutes_dif}"

                elif minutes_dif == 0:
                    time_dif_display_str = "On time"

                else:
                    time_dif_display_str = f"+{minutes_dif}"
                    on_time = False
                scheduled_display_str = f"Scheduled: {scheduled_formatted} | {time_dif_display_str}"


            else:
                scheduled_display_str = "Schedule N/A"


            #calculate minutes remaining
            minutes = (arrival_time_ms - current_time_ms) // (1000 * 60)

            #Format raw milliseconds into a readable time
            formatted_time = datetime.fromtimestamp(arrival_time_ms / 1000).strftime("%I:%M %p")

            # Combine time + minutes remaining
            if minutes <= 0:
                time_display_str = f"{formatted_time} | Arriving Now"
            else:
                time_display_str = f"{formatted_time} | {minutes} min"

            if "loadPercentage" in arrival:
                load_percent = f"{arrival['loadPercentage']}% full"
            else:
                load_percent = "Load percentage is N/A for this bus"

            #GTK UI construction
            self.individual_arrival_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.individual_arrival_box.get_style_context().add_class("individual_arrival_box")

            #Route short sign
            self.arrivalShortSign = Gtk.Label(label=f"{short_sign}")
            self.arrivalShortSign.get_style_context().add_class("short_sign")
            self.individual_arrival_box.add(self.arrivalShortSign)
            self.arrivalShortSign.show_all()

            #Estimated/actual arrival time
            self.arrivalTime = Gtk.Label(label=time_display_str)
            self.arrivalTime.get_style_context().add_class("arrival_time")
            self.individual_arrival_box.add(self.arrivalTime)
            self.arrivalTime.show_all()

            #Scheduled time
            self.scheduledTime = Gtk.Label(label=scheduled_display_str)
            if on_time == True:
                self.scheduledTime.get_style_context().add_class("scheduled_time_OT")
            else:
                self.scheduledTime.get_style_context().add_class("scheduled_time_Late")
            self.individual_arrival_box.add(self.scheduledTime)

            #Load percentage
            self.arrival_load_percent = Gtk.Label(label=load_percent)
            self.arrival_load_percent.get_style_context().add_class("load_percent")
            self.individual_arrival_box.add(self.arrival_load_percent)
            self.arrival_load_percent.show_all()

            self.arrivals_box.add(self.individual_arrival_box)
            self.arrivals_box.show_all()

#Added refresh method
    def refresh(self):
        if self.last_combo is not None:
            print("Auto-refreshing arrival times...")
            self.on_stop_selected(self.last_combo)
        return True

win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
