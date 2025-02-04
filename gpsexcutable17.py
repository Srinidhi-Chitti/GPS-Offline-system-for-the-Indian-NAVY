from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QMenuBar, QAction, QTabWidget, QMessageBox,
    QFileDialog, QGroupBox
)
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from geopy.distance import geodesic
import os
import folium
from gps_database4 import GPSDatabase
from serial_comm_handler5t import SerialCommunication

class GPSMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPS Coordinates Map")
        self.setGeometry(100, 100, 1024, 768)  # Set initial size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.db = GPSDatabase()
        self.serial_comm = None
        self.map_view = None
        self.map_file = "map.html"

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()  # Main layout is now QHBoxLayout
        self.central_widget.setLayout(main_layout)

        # Left side for controls, logos, COM settings, and tracking options
        left_layout = QVBoxLayout()

        # Group logos, COM settings, and tracking options into one compact layout
        compact_group = QGroupBox("Controls and Settings")
        compact_layout = QVBoxLayout()

        compact_layout.addWidget(self.create_logo_group())
        compact_layout.addWidget(self.create_com_port_controls())
        compact_layout.addWidget(self.create_tracking_controls())

        compact_group.setLayout(compact_layout)
        left_layout.addWidget(compact_group)

        main_layout.addLayout(left_layout, stretch=1)  # Stretch factor 1 for left

        # Right side for map (increased size)
        self.map_view = QWebEngineView()  # Initialize map_view here
        self.init_map()  # Initialize the map
        main_layout.addWidget(self.map_view, stretch=3)  # Stretch factor 3 for right

        self.add_menu()  # Keep menu addition
        self.populate_phone_numbers()

    def add_menu(self):
        menubar = QMenuBar(self)
        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Help")
        instructions_action = QAction("Instructions", self)
        instructions_action.triggered.connect(self.show_instructions)
        help_menu.addAction(instructions_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        self.setMenuBar(menubar)

    def create_logo_group(self):  # Helper function for logos
        logo_group = QGroupBox("Logos")
        logo_layout = QHBoxLayout()

        logo1 = QLabel()
        pixmap1 = QPixmap("gitam.jpg").scaled(300, 200, QtCore.Qt.KeepAspectRatio)
        logo1.setPixmap(pixmap1)

        logo2 = QLabel()
        pixmap2 = QPixmap("navy.png").scaled(300,200,QtCore.Qt.KeepAspectRatio)
        logo2.setPixmap(pixmap2)

        logo_layout.addWidget(logo1, alignment=Qt.AlignLeft)
        logo_layout.addWidget(logo2, alignment=Qt.AlignRight)

        logo_group.setLayout(logo_layout)
        return logo_group

    def create_com_port_controls(self):  # Helper function
        com_group = QGroupBox("COM Port Settings")
        com_layout = QVBoxLayout()
        com_layout.setContentsMargins(5, 5, 5, 5)  # Compact margins

        self.com_port_combo = QComboBox()
        self.update_com_ports()
        com_layout.addWidget(self.com_port_combo)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_serial)
        com_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        com_layout.addWidget(self.disconnect_button)

        com_group.setLayout(com_layout)
        return com_group

    def create_tracking_controls(self):  # Helper function
        tracking_group = QGroupBox("Tracking Options")
        tracking_layout = QVBoxLayout()
        tracking_layout.setContentsMargins(5, 5, 5, 5)  # Compact margins

        self.phone_number_combo = QComboBox()
        self.phone_number_combo.currentIndexChanged.connect(self.update_dates)
        tracking_layout.addWidget(self.phone_number_combo)

        self.date_combo = QComboBox()
        tracking_layout.addWidget(self.date_combo)

        self.show_route_button = QPushButton("Show Route")
        self.show_route_button.clicked.connect(self.show_route)
        tracking_layout.addWidget(self.show_route_button)

        self.clear_markers_button = QPushButton("Clear Markers")
        self.clear_markers_button.clicked.connect(self.clear_markers)
        tracking_layout.addWidget(self.clear_markers_button)

        self.calculate_distance_button = QPushButton("Calculate Distance")
        self.calculate_distance_button.clicked.connect(self.calculate_distance)
        tracking_layout.addWidget(self.calculate_distance_button)

        tracking_group.setLayout(tracking_layout)
        return tracking_group

    def update_com_ports(self):
        self.com_port_combo.clear()
        ports = ["COM1", "COM2", "COM3"]  # Replace with actual serial port detection logic
        self.com_port_combo.addItems(ports)

    def connect_to_serial(self):
        com_port = self.com_port_combo.currentText()
        if com_port:
            try:
                self.serial_comm = SerialCommunication(com_port)
                self.serial_comm.configure_for_sms()
                QMessageBox.information(self, "Connected", f"Connected to {com_port}")
                self.connect_button.setEnabled(False)
                self.disconnect_button.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", str(e))

    def disconnect_serial(self):
        if self.serial_comm:
            self.serial_comm.serial_port.close()
            self.serial_comm = None
            QMessageBox.information(self, "Disconnected", "Disconnected from COM port")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)

    def populate_phone_numbers(self):
        phone_numbers = self.db.get_all_phone_numbers_with_ids()
        self.phone_number_combo.clear()
        for phone_id, phone_number in phone_numbers:
            self.phone_number_combo.addItem(f"ID: {phone_id} - {phone_number}", phone_id)
        if phone_numbers:
            self.update_dates()

    def update_dates(self):
        current_phone_id = self.phone_number_combo.currentData()
        if current_phone_id is not None:
            dates = self.db.get_all_dates_for_number(current_phone_id)
            self.date_combo.clear()
            self.date_combo.addItems(dates)

    def show_route(self):
        current_phone_id = self.phone_number_combo.currentData()
        selected_date = self.date_combo.currentText()
        if current_phone_id and selected_date:
            coordinates = self.db.get_coordinates_for_id_and_date(current_phone_id, selected_date)
            if coordinates:
                self.update_map(coordinates)
                QMessageBox.information(self, "Route Loaded", f"Loaded {len(coordinates)} points.")
            else:
                QMessageBox.warning(self, "No Data", "No coordinates found for the selected date.")

    def clear_markers(self):
        self.init_map()  # Reset the map
        QMessageBox.information(self, "Clear Markers", "All markers have been cleared.")

    def calculate_distance(self):
        current_phone_id = self.phone_number_combo.currentData()
        selected_date = self.date_combo.currentText()
        if current_phone_id and selected_date:
            coordinates = self.db.get_coordinates_for_id_and_date(current_phone_id, selected_date)
            if len(coordinates) >= 2:
                total_distance = sum(
                    geodesic((coordinates[i][0], coordinates[i][1]), (coordinates[i + 1][0], coordinates[i + 1][1])).km
                    for i in range(len(coordinates) - 1)
                )
                QMessageBox.information(self, "Total Distance", f"Total distance: {total_distance:.2f} km")
            else:
                QMessageBox.warning(self, "Insufficient Data", "At least two points are required to calculate distance.")

    def init_map(self):
        folium_map = folium.Map(location=[17.4444, 78.3555], zoom_start=15)
        folium_map.save(self.map_file)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(self.map_file)))

    def update_map(self, coordinates):
        initial_location = (coordinates[0][0], coordinates[0][1])
        folium_map = folium.Map(location=initial_location, zoom_start=15)

        for i, (lat, lon, timestamp) in enumerate(coordinates):
            if i == 0:
                folium.Marker([lat, lon], popup="<b>START</b>", icon=folium.Icon(color="green")).add_to(folium_map)
            elif i == len(coordinates) - 1:
                folium.Marker([lat, lon], popup="<b>END</b>", icon=folium.Icon(color="red")).add_to(folium_map)
            else:
                folium.CircleMarker([lat, lon], radius=5, color="black", fill=True, fill_opacity=0.7, popup=f"{timestamp}").add_to(folium_map)

        folium.PolyLine([(lat, lon) for lat, lon, _ in coordinates], color="blue").add_to(folium_map)

        folium_map.save(self.map_file)
        self.map_view.setUrl(QUrl.fromLocalFile(os.path.abspath(self.map_file)))

    def show_instructions(self):
        QMessageBox.information(
            self,
            "Instructions",
            "1. Connect to the correct COM port.\n2. Select a phone number and date.\n3. Use the tracking options to manage GPS data."
        )

    def show_about(self):
        QMessageBox.information(self, "About", "GPS Vehicle Tracking Application\nVersion: 1.0")

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = GPSMapApp()
    window.showMaximized()  # Make the window full screen
    sys.exit(app.exec_())