import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import random

# Mock GPS data for vehicles
vehicle_data = {
    "V001": (17.6868, 83.2185),  # Example: Visakhapatnam Port Coordinates
    "V002": (17.6898, 83.2075),
    "V003": (17.6930, 83.2021),
    "V004": (17.6881, 83.2197),
    "V005": (17.6852, 83.2109),
}

class MapCanvas(FigureCanvas):
    """Class to plot the map on the PyQt5 interface."""
    def __init__(self, parent=None):
        self.figure, self.ax = plt.subplots()
        super().__init__(self.figure)
        self.setParent(parent)

    def plot_map(self, vehicle_id=None, location=None):
        self.ax.clear()
        # Base map (static)
        self.ax.set_title("Naval Base - Vehicle Tracking")
        self.ax.set_xlim(17.68, 17.70)
        self.ax.set_ylim(83.20, 83.22)
        self.ax.set_xlabel("Latitude")
        self.ax.set_ylabel("Longitude")

        # Plot all vehicles
        for vid, loc in vehicle_data.items():
            self.ax.plot(loc[1], loc[0], 'bo', label=vid if vid != vehicle_id else f"{vid} (Selected)")

        # Highlight selected vehicle
        if vehicle_id and location:
            self.ax.plot(location[1], location[0], 'ro', markersize=10)
            self.ax.text(location[1], location[0], f" {vehicle_id}", fontsize=9, color='red')

        self.ax.legend()
        self.draw()


class VehicleTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Naval Base Vehicle Tracker")
        self.setGeometry(100, 100, 800, 600)

        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layouts
        self.layout = QVBoxLayout(self.central_widget)

        # Input label and field
        self.label = QLabel("Enter Vehicle ID:")
        self.layout.addWidget(self.label)

        self.vehicle_id_input = QLineEdit()
        self.vehicle_id_input.setPlaceholderText("e.g., V001")
        self.layout.addWidget(self.vehicle_id_input)

        # Track Button
        self.track_button = QPushButton("Track Vehicle")
        self.track_button.clicked.connect(self.track_vehicle)
        self.layout.addWidget(self.track_button)

        # Map Canvas
        self.map_canvas = MapCanvas(self)
        self.layout.addWidget(self.map_canvas)

        # Default Map Plot
        self.map_canvas.plot_map()

    def track_vehicle(self):
        vehicle_id = self.vehicle_id_input.text().strip().upper()

        # Validate vehicle ID
        if vehicle_id in vehicle_data:
            location = vehicle_data[vehicle_id]
            self.map_canvas.plot_map(vehicle_id, location)
        else:
            QMessageBox.warning(self, "Error", "Invalid Vehicle ID. Please try again!")

# Main application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = VehicleTrackerApp()
    main_window.show()
    sys.exit(app.exec_())
