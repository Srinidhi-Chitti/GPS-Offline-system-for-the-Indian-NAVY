import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QLabel, QFrame, QComboBox, QPushButton, QTabWidget, QHBoxLayout, QMenuBar, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PIL import Image
from gps_database4 import GPSDatabase
from serial_comm_handler5t import SerialCommunication
import re
import geopy.distance
import queue
import serial.tools.list_ports
import csv
import os
import threading


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.setToolTip(self.text)

    def show_tooltip(self):
        if self.tooltip:
            self.tooltip.hide()
        self.tooltip = QtWidgets.QToolTip()
        self.tooltip.showText(self.widget.mapToGlobal(QtCore.QPoint(0, 0)), self.text)

    def hide_tooltip(self):
        if self.tooltip:
            self.tooltip.hide()
            self.tooltip = None


class GPSMapApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Coordinates Map")
        self.setGeometry(100, 100, 1200, 800)
        self.date_labels = {}

        self.setup_styles()
        self.logo1 = self.load_and_resize_image("gitam.jpg", (120, 60))
        self.logo2 = self.load_and_resize_image("navy.png", (70, 70))

        self.main_layout = QVBoxLayout()
        central_widget = QtWidgets.QWidget(self)
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

        self.add_logos()

        # Use regular variables instead of pyqtSignal
        self.phone_number_var = ""  # Use a regular string variable
        self.com_port_var = ""       # Use a regular string variable
        self.date_var = ""           # Use a regular string variable
        self.map_markers = {}
        self.polylines = {}
        self.time_labels = {}
        self.date_labels = {}

        self.create_widgets()
        self.create_menu()

        self.db = GPSDatabase()
        self.serial_comm = None

        self.sms_queue = queue.Queue()

        self.update_phone_number_menu()

        self.process_queue()

    def add_logos(self):
        logo1_label = QLabel(self)
        logo1_label.setPixmap(QPixmap(self.logo1))
        logo1_label.setStyleSheet("background-color: white;")
        logo1_label.setGeometry(50, 10, 120, 60)

        logo2_label = QLabel(self)
        logo2_label.setPixmap(QPixmap(self.logo2))
        logo2_label.setStyleSheet("background-color: white;")
        logo2_label.setGeometry(self.width() - 80, 10, 70, 70)

    def load_and_resize_image(self, image_path, size):
        img = Image.open(image_path)
        img_resized = img.resize(size, Image.LANCZOS)
        img_resized.save("temp_image.png")
        return "temp_image.png"

    def setup_styles(self):
        self.setStyleSheet("background-color: white; font-family: Arial; font-size: 10pt;")

    def create_widgets(self):
        self.search_frame = QFrame(self)
        self.search_frame.setLayout(QVBoxLayout())
        self.main_layout.addWidget(self.search_frame)

        self.search_label = QLabel("  GPS Vehicle Tracking System   ", self)
        self.search_label.setStyleSheet("color: #006b65; font-size: 20pt;")
        self.search_frame.layout().addWidget(self.search_label)

        self.tab_control = QTabWidget(self)
        self.main_layout.addWidget(self.tab_control)

        self.download_csv_button = QPushButton("Download CSV", self)
        self.download_csv_button.clicked.connect(self.download_database_csv)
        self.main_layout.addWidget(self.download_csv_button)

        self.com_tracking_frame = QFrame(self)
        self.com_tracking_frame.setLayout(QVBoxLayout())
        self.main_layout.addWidget(self.com_tracking_frame)

        self.com_port_frame = QFrame(self.com_tracking_frame)
        self.com_port_frame.setLayout(QVBoxLayout())
        self.com_tracking_frame.layout().addWidget(self.com_port_frame)

        self.com_port_menu = QComboBox(self.com_port_frame)
        self.com_port_frame.layout().addWidget(self.com_port_menu)
        ToolTip(self.com_port_menu, "Select COM port")

        self.connect_button = QPushButton("Connect", self.com_port_frame)
        self.connect_button.clicked.connect(self.connect_to_serial)
        self.com_port_frame.layout().addWidget(self.connect_button)
        ToolTip(self.connect_button, "Connect to selected COM port")

        self.disconnect_button = QPushButton("Disconnect", self.com_port_frame)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.disconnect_button.setEnabled(False)
        self.com_port_frame.layout().addWidget(self.disconnect_button)
        ToolTip(self.disconnect_button, "Disconnect from the serial port")

        self.tracking_frame = QFrame(self.com_tracking_frame)
        self.tracking_frame.setLayout(QVBoxLayout())
        self.com_tracking_frame.layout().addWidget(self.tracking_frame)

        self.phone_number_menu = QComboBox(self.tracking_frame)
        self.tracking_frame.layout().addWidget(self.phone_number_menu)
        ToolTip(self.phone_number_menu, "Select a phone number")

        self.date_menu = QComboBox(self.tracking_frame)
        self.tracking_frame.layout().addWidget(self.date_menu)
        ToolTip(self.date_menu, "Select a date")

        self.show_route_button = QPushButton("Show Route", self.tracking_frame)
        self.show_route_button.clicked.connect(self.show_route)
        self.tracking_frame.layout().addWidget(self.show_route_button)
        ToolTip(self.show_route_button, "Show route for the selected phone number and date")

        self.clear_button = QPushButton("Clear Markers", self.tracking_frame)
        self.clear_button.clicked.connect(self.clear_markers)
        self.tracking_frame.layout().addWidget(self.clear_button)
        ToolTip(self.clear_button, "Clear all markers from the map")

        self.navigate_button = QPushButton("Navigate to Latest Marker", self.tracking_frame)
        self.navigate_button.clicked.connect(self.navigate_to_latest_marker)
        self.tracking_frame.layout().addWidget(self.navigate_button)
        ToolTip(self.navigate_button, "Zoom to the latest marker")

        self.distance_button = QPushButton("Calculate Distance", self.tracking_frame)
        self.distance_button.clicked.connect(self.calculate_distance)
        self.tracking_frame.layout().addWidget(self.distance_button)
        ToolTip(self.distance_button, "Calculate distance between the last two markers")

    def create_menu(self):
        menubar = self.menuBar()  # Use menuBar() method of QMainWindow
        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")
        phone_numbers_action = QAction("ID - Phone Numbers", self)
        phone_numbers_action.triggered.connect(self.show_phone_numbers)
        view_menu.addAction(phone_numbers_action)

        help_menu = menubar.addMenu("Help")
        instructions_action = QAction("Instructions", self)
        instructions_action.triggered.connect(self.show_instructions)
        help_menu.addAction(instructions_action)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_info)
        help_menu.addAction(about_action)

    def show_instructions(self):
        QMessageBox.information(
            self,
            "Instructions to use",
            "1. Check the COM port of the connected module in the device manager's Ports.\n"
            "2. Select the correct COM port and click on Connect.\n"
            "3. Once the connection is established, you will be able to receive GPS data.\n"
            "4. Use the Tracking Options to view routes, navigate, and calculate distances.",
        )

    def show_about_info(self):
        QMessageBox.information(
            self,
            "About",
            "Application name: GPS Vehicle Tracking\nVersion: 1.0\nAuthors: Sri Rohit, Praveen, Ananya.",
        )

    def show_phone_numbers(self):
        phone_numbers_with_ids = self.db.get_all_phone_numbers_with_ids()
        phone_numbers_list = "\n".join(
            [f"ID: {phone_id}, Phone Number: {phone_number}" for phone_id, phone_number in phone_numbers_with_ids]
        )
        QMessageBox.information(self, "Phone Numbers", phone_numbers_list)

    def process_queue(self):
        try:
            while True:
                phone_number, time_value, lat, lon = self.sms_queue.get_nowait()
                if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
                    phone_number_id = self.db.insert_coordinates(phone_number, time_value, lat, lon)
                    self.update_map(phone_number_id, lat, lon)
                    self.update_phone_number_menu()
                    self.update_date_menu()
        except queue.Empty:
            pass
        QtCore.QTimer.singleShot(100, self.process_queue)

    def download_database_csv(self):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop/gps")
        csv_file_path = os.path.join(desktop_path, "gps_coordinates.csv")

        try:
            with open(csv_file_path, mode='w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["Phone Number", "Latitude", "Longitude", "Timestamp", "Date"])
                self.db.cursor.execute("""
                    SELECT phone_numbers.phone_number, coordinates.latitude, coordinates.longitude, coordinates.timestamp, coordinates.date 
                    FROM coordinates
                    JOIN phone_numbers ON coordinates.phone_number_id = phone_numbers.id
                """)
                rows = self.db.cursor.fetchall()
                for row in rows:
                    writer.writerow(row)

            QMessageBox.information(self, "Success", f"Database successfully exported to CSV at {csv_file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting database to CSV: {e}")

    def create_map_tab(self, phone_number_id):
        tab = QWidget()
        self.tab_control.addTab(tab, f"ID: {phone_number_id}")
        self.map_markers[phone_number_id] = []
        self.polylines[phone_number_id] = None
        return tab

    def select_phone_number(self, phone_number_id):
        self.phone_number_var = phone_number_id
        self.phone_number_menu.setCurrentText(self.phone_number_var)
        map_widget = self.get_map_widget(phone_number_id)
        self.tab_control.setCurrentWidget(map_widget)

    def get_map_widget(self, phone_number_id):
        for i in range(self.tab_control.count()):
            if self.tab_control.tabText(i) == f"ID: {phone_number_id}":
                return self.tab_control.widget(i)
        return self.create_map_tab(phone_number_id)

    def update_map(self, phone_number_id, lat, lon):
        map_widget = self.get_map_widget(phone_number_id)

        if phone_number_id not in self.map_markers:
            self.map_markers[phone_number_id] = []
            self.polylines[phone_number_id] = None

        # Set the map position and zoom level
        # Assuming you have a method to set the position and zoom level in your map widget
        # map_widget.set_position(lat, lon)
        # map_widget.set_zoom(15)

        marker = None  # Replace with actual marker creation logic
        self.map_markers[phone_number_id].append(marker)

        self.update_polyline(phone_number_id)

        date = self.date_var
        if phone_number_id in self.date_labels:
            self.date_labels[phone_number_id].setText(f"Date: {date}")

        self.update()

    def update_polyline(self, phone_number_id):
        map_widget = self.get_map_widget(phone_number_id)

        if self.polylines[phone_number_id]:
            # Delete existing polyline if it exists
            pass  # Replace with actual deletion logic

        lat_lon_list = [
            (marker.position[0], marker.position[1]) for marker in self.map_markers[phone_number_id]
        ]

        if len(lat_lon_list) >= 2:
            self.polylines[phone_number_id] = None  # Replace with actual polyline creation logic

    def clear_markers(self):
        phone_number_id = self.phone_number_var
        if phone_number_id in self.map_markers:
            map_widget = self.get_map_widget(phone_number_id)

            for marker in self.map_markers[phone_number_id]:
                # Delete marker logic here
                pass
            self.map_markers[phone_number_id].clear()

            if self.polylines[phone_number_id]:
                # Delete polyline logic here
                self.polylines[phone_number_id] = None

            # Reset the map view
            # map_widget.set_position(0, 0)
            # map_widget.set_zoom(2)

    def navigate_to_latest_marker(self):
        phone_number_id = self.phone_number_var
        if phone_number_id in self.map_markers and self.map_markers[phone_number_id]:
            latest_marker = self.map_markers[phone_number_id][-1]
            lat, lon = latest_marker.position  # Assuming 'position' is a tuple (lat, lon)
            map_widget = self.get_map_widget(phone_number_id)
            # map_widget.set_position(lat, lon)
            # map_widget.set_zoom(15)
        else:
            QMessageBox.information(self, "No Markers", "No markers available to navigate to.")

    def calculate_distance(self):
        phone_number_id = self.phone_number_var
        if phone_number_id in self.map_markers and len(self.map_markers[phone_number_id]) >= 2:
            total_distance = 0.0
            for i in range(len(self.map_markers[phone_number_id]) - 1):
                coords_1 = (
                    self.map_markers[phone_number_id][i].position[0],
                    self.map_markers[phone_number_id][i].position[1],
                )
                coords_2 = (
                    self.map_markers[phone_number_id][i + 1].position[0],
                    self.map_markers[phone_number_id][i + 1].position[1],
                )
                total_distance += geopy.distance.distance(coords_1, coords_2).km

            QMessageBox.information(
                self,
                "Total Distance",
                f"Total length of the polyline: {total_distance:.2f} km",
            )
        else:
            QMessageBox.information(
                self,
                "Insufficient Data",
                "At least two markers are needed to calculate the polyline length."
            )

    def show_route(self):
        phone_number_id = self.phone_number_var
        date = self.date_var
        if (
            phone_number_id
            and date
            and phone_number_id != "No data available"
            and date != "No data available"
        ):
            self.clear_markers()
            coordinates = self.db.get_coordinates_for_id_and_date(phone_number_id, date)
            if coordinates:
                for lat, lon, time_value in coordinates:
                    self.update_map(phone_number_id, lat, lon)

                if phone_number_id in self.date_labels:
                    self.date_labels[phone_number_id].setText(f"Date: {date}")
            else:
                QMessageBox.information(self, "No Data", "No data available for the selected date.")
                if phone_number_id in self.date_labels:
                    self.date_labels[phone_number_id].setText("Date: No data available")
        else:
            QMessageBox.information(
                self,
                "No Data",
                "No data available for the selected phone number and date.",
            )
            if phone_number_id in self.date_labels:
                self.date_labels[phone_number_id].setText("Date: No data available")

    def update_phone_number_menu(self):
        phone_numbers_with_ids = self.db.get_all_phone_numbers_with_ids()
        if phone_numbers_with_ids:
            self.phone_number_var = phone_numbers_with_ids[0][0]  # Set the variable directly
            self.phone_number_menu.setCurrentText(self.phone_number_var)  # Update the QComboBox
        else:
            self.phone_number_var = "No data available"  # Set the variable directly
            self.phone_number_menu.clear()  # Clear the menu if no data is available
            self.phone_number_menu.addItem(self.phone_number_var)  # Add the "No data available" item
        self.update_date_menu()

    def update_date_menu(self):
        phone_number_id = self.phone_number_var

        if phone_number_id and phone_number_id != "No data available":
            dates = self.db.get_all_dates_for_number(phone_number_id)
        else:
            dates = []

        if dates:
            self.date_var = dates[0]  # Set the variable directly
        else:
            self.date_var = "No data available"  # Set the variable directly

        self.date_menu.clear()
        for date in dates:
            self.date_menu.addItem(date)

        if not dates:
            self.show_route_button.setEnabled(False)
            if hasattr(self, 'date_labels') and phone_number_id in self.date_labels:
                self.date_labels[phone_number_id].setText("No dates available")
        else:
            self.show_route_button.setEnabled(True)
            if hasattr(self, 'date_labels') and phone_number_id in self.date_labels:
                self.date_labels[phone_number_id].setText(f"Date: {dates[0]}")

        print(f"Updated date menu for phone_number_id {phone_number_id}: {dates}")

    def wait_for_sms(self):
        while True:
            if self.serial_comm and self.serial_comm.serial_port.in_waiting > 0:
                response = self.serial_comm.serial_port.read(
                    self.serial_comm.serial_port.in_waiting
                ).decode("utf-8")
                match = re.search(r'\+CMTI: "SM",(\d+)', response)
                if match:
                    index = match.group(1)
                    phone_number, time_value, locations = self.serial_comm.read_sms(index)

                    if phone_number and locations:
                        for lat, lon in locations:
                            self.sms_queue.put((phone_number, time_value, lat, lon))

                        self.serial_comm.delete_all_sms()

    def update_com_port_menu(self):
        ports = serial.tools.list_ports.comports()
        com_ports = [port.device for port in ports]

        if com_ports:
            self.com_port_var = com_ports[0]  # Set the variable directly
        else:
            self.com_port_var = "No COM ports available"  # Set the variable directly

        self.com_port_menu.clear()
        if com_ports:
            for com_port in com_ports:
                self.com_port_menu.addItem(com_port)
        else:
            self.com_port_menu.addItem("No COM ports available")

    def connect_to_serial(self):
        com_port = self.com_port_var
        if com_port and com_port != "No COM ports available":
            try:
                self.serial_comm = SerialCommunication(com_port)
                self.serial_comm.configure_for_sms()
                threading.Thread(target=self.wait_for_sms, daemon=True).start()
                self.connect_button.setEnabled(False)
                self.disconnect_button.setEnabled(True)
                QMessageBox.information(self, "Connected", "Serial Connection is established.")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to connect to {com_port}. Ensure it is the correct port and try again.\n\nError: {e}",
                )
        else:
            QMessageBox.critical(self, "Error", "No COM port selected or available.")

    def disconnect_serial(self):
        if self.serial_comm:
            try:
                self.serial_comm.serial_port.close()
                self.serial_comm = None
                self.connect_button.setEnabled(True)
                self.disconnect_button.setEnabled(False)
                QMessageBox.information(self, "Disconnected", "Serial connection closed.")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to disconnect properly.\n\nError: {e}",
                )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = GPSMapApp()
    window.show()
    sys.exit(app.exec_())