import tkinter as tk
from ttkthemes import ThemedTk
from tkintermapview import TkinterMapView
import threading
#from a import GPSDatabase,SerialCommunication
from gps_database4 import GPSDatabase
from serial_comm_handler5t import SerialCommunication
import re
import tkinter.messagebox as tk_messagebox
import geopy.distance
import queue
from tkinter import ttk
import serial.tools.list_ports
from tkinter import PhotoImage
from PIL import Image, ImageTk
from tkinter import filedialog, ttk, messagebox
import csv
import os


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tooltip,
            text=self.text,
            background="lightyellow",
            relief="solid",
            borderwidth=1,
        )
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class GPSMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GPS Coordinates Map")
        self.root.state("zoomed")
        self.date_labels = {}

        self.setup_styles()
        self.logo1 = self.load_and_resize_image("gitam.jpg", (120, 60))
        self.logo2 = self.load_and_resize_image("navy.png", (70, 70))


        self.main_frame = ttk.Frame(self.root, padding="30 10 30 30")
        self.main_frame.pack(fill="both", expand=True)
        
        self.add_logos()

        self.phone_number_var = tk.StringVar()
        self.com_port_var = tk.StringVar()
        self.date_var = tk.StringVar()
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

        self.root.after(100, self.process_queue)


    def add_logos(self):
    # Add logo in the top-left corner
      self.logo1_label = tk.Label(self.root, image=self.logo1, background="white")
      self.logo1_label.place(x=50, y=10, anchor="nw")

    # Add logo in the top-right corner
      self.logo2_label = tk.Label(self.root, image=self.logo2, background="white")
      self.logo2_label.place(x=self.root.winfo_width() - 10, y=10, anchor="ne")

    # Bind window resize event to update logo positions
      self.root.bind("<Configure>", self.update_logo_positions)
    

    def load_and_resize_image(self, image_path, size):
        # Open image
        with Image.open(image_path) as img:
            # Resize image
            img_resized = img.resize(size, Image.LANCZOS)
            # Convert to PhotoImage
            return ImageTk.PhotoImage(img_resized)
        
    def update_logo_positions(self, event):
      self.logo2_label.place(x=self.root.winfo_width() - self.logo2_label.winfo_width() , y=10, anchor="ne")
    

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TFrame", background="white")   #006b65

    def create_widgets(self):
     

     style = ttk.Style()
     #style.configure("COMPortSettings.TLabelframe", background="#006b65")
    
    
     self.search_frame = ttk.Frame(self.main_frame, padding="15")
     self.search_frame.pack(pady=10)

     self.search_label = ttk.Label(self.search_frame, text="  GPS Vehicle Tracking System   ", background="white",foreground="#006b65", font=("Arial", 20))
     self.search_label.pack(side="left", padx=0)

     self.tab_control = ttk.Notebook(self.main_frame)
     self.tab_control.pack(side="left", fill="both", expand=True)


     self.download_csv_button = tk.Button(self.root, text="Download CSV", command=self.download_database_csv)
     self.download_csv_button.pack(pady=10)  # Adjust positioning as needed

    # Combined frame for COM Port Settings and Tracking Options
     self.com_tracking_frame = ttk.LabelFrame(self.main_frame, text="Accessibility options ", padding="10",style="COMPortSettings.TLabelframe")
     self.com_tracking_frame.pack(side="left", fill="y", padx=10, pady=10, anchor="n")

    # COM Port Settings Frame
     self.com_port_frame = ttk.LabelFrame(self.com_tracking_frame, text="COM Port Settings", padding="10")
     self.com_port_frame.pack(pady=5, fill="x")
     
     self.com_port_menu = ttk.OptionMenu(self.com_port_frame, self.com_port_var, "")
     self.com_port_menu.pack(pady=5, anchor="w")
     self.update_com_port_menu()
     ToolTip(self.com_port_menu, "Select COM port")

     self.connect_button = ttk.Button(
        self.com_port_frame, text="Connect", command=self.connect_to_serial
    )
     self.connect_button.pack(pady=5, anchor="w")
     ToolTip(self.connect_button, "Connect to selected COM port")

     self.disconnect_button = ttk.Button(
        self.com_port_frame,
        text="Disconnect",
        command=self.disconnect_serial,
        state="disabled",
    )
     self.disconnect_button.pack(pady=5, anchor="w")
     ToolTip(self.disconnect_button, "Disconnect from the serial port")

    # Tracking Options Frame
     self.tracking_frame = ttk.LabelFrame(self.com_tracking_frame, text="Tracking Options", padding="10")
     self.tracking_frame.pack(pady=5, fill="x")

     self.phone_number_menu = ttk.OptionMenu(
        self.tracking_frame, self.phone_number_var, ""
    )
     self.phone_number_menu.pack(pady=5, anchor="w")
     ToolTip(self.phone_number_menu, "Select a phone number")

     self.date_menu = ttk.OptionMenu(self.tracking_frame, self.date_var, "")
     self.date_menu.pack(pady=5, anchor="w")
     ToolTip(self.date_menu, "Select a date")

     self.show_route_button = ttk.Button(
        self.tracking_frame, text="Show Route", command=self.show_route
    )
     self.show_route_button.pack(pady=5, anchor="w")
     ToolTip(
        self.show_route_button,
        "Show route for the selected phone number and date",
    )

     self.clear_button = ttk.Button(
        self.tracking_frame, text="Clear Markers", command=self.clear_markers
    )
     self.clear_button.pack(pady=5, anchor="w")
     ToolTip(
        self.clear_button,
        "Clear all markers from the map",
    )

     self.navigate_button = ttk.Button(
        self.tracking_frame,
        text="Navigate to Latest Marker",
        command=self.navigate_to_latest_marker,
    )
     self.navigate_button.pack(pady=5, anchor="w")
     ToolTip(
        self.navigate_button,
        "Zoom to the latest marker",
    )

     self.distance_button = ttk.Button(
    self.tracking_frame,
        text="Calculate Distance",                                   #calculate distance button disalbed
        command=self.calculate_distance,
    )
     self.distance_button.pack(pady=5, anchor="w")
     ToolTip(
        self.distance_button,
        "Calculate distance between the last two markers",
    )

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="ID - Phone Numbers", command=self.show_phone_numbers)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Instructions", command=self.show_instructions)
        help_menu.add_command(label="About", command=self.show_about_info)

    def show_instructions(self):
        tk_messagebox.showinfo(
            "Instructions to use",
            "1. Check the COM port of the connected module in the device manager's Ports.\n"
            "2. Select the correct COM port and click on Connect.\n"
            "3. Once the connection is established, you will be able to receive GPS data.\n"
            "4. Use the Tracking Options to view routes, navigate, and calculate distances.",
        )

    def show_about_info(self):
        tk_messagebox.showinfo(
            "About",
            "Application name: GPS Vehicle Tracking\nVersion: 1.0\nAuthors: Sri Rohit, Praveen, Ananya.",
        )

    def show_phone_numbers(self):
        phone_numbers_with_ids = self.db.get_all_phone_numbers_with_ids()
        phone_numbers_list = "\n".join(
            [f"ID: {phone_id}, Phone Number: {phone_number}" for phone_id, phone_number in phone_numbers_with_ids]
        )
        tk_messagebox.showinfo("Phone Numbers", phone_numbers_list)

    def process_queue(self):
     try:
        while True:
            phone_number, time_value, lat, lon = self.sms_queue.get_nowait()
            if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
                # Pass time_value to insert_coordinates
                phone_number_id = self.db.insert_coordinates(phone_number, time_value, lat, lon)
                self.update_map(phone_number_id, lat, lon)
                self.update_phone_number_menu() 
                self.update_date_menu() 
     except queue.Empty:
        pass
     self.root.after(100, self.process_queue)



    def download_database_csv(self):
    # Define the file path (saving on the Desktop)
     desktop_path = os.path.join(os.path.expanduser("~"), "Desktop/gps")
     csv_file_path = os.path.join(desktop_path, "gps_coordinates.csv")

     try:
        # Open the file for writing
        with open(csv_file_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            
            # Write the header row
            writer.writerow(["Phone Number", "Latitude", "Longitude", "Timestamp", "Date"])
            
            # Fetch the data from the database
            self.db.cursor.execute("""
                SELECT phone_numbers.phone_number, coordinates.latitude, coordinates.longitude, coordinates.timestamp, coordinates.date 
                FROM coordinates
                JOIN phone_numbers ON coordinates.phone_number_id = phone_numbers.id
            """)
            rows = self.db.cursor.fetchall()
            
            # Write each row of data to the CSV file
            for row in rows:
                writer.writerow(row)

        messagebox.showinfo("Success", f"Database successfully exported to CSV at {csv_file_path}")
     except Exception as e:
        # Show an error message box
        messagebox.showerror("Error", f"Error exporting database to CSV: {e}")


    def create_map_tab(self, phone_number_id):
        tab = ttk.Frame(self.tab_control)
        map_widget = TkinterMapView(tab, width=800, height=500, borderwidth=2, relief="solid")
        map_widget.pack(fill="both", expand=True)
        map_widget.set_position(0, 0)
        map_widget.set_zoom(2)


        self.tab_control.add(tab, text=f"ID: {phone_number_id}")
        self.map_markers[phone_number_id] = []
        self.polylines[phone_number_id] = None
       

        return map_widget
    

    def select_phone_number(self, phone_number_id):
        self.phone_number_var.set(phone_number_id)
        map_widget = self.get_map_widget(phone_number_id)
        self.tab_control.select(map_widget.master)

    def get_map_widget(self, phone_number_id):
        for i in range(self.tab_control.index("end")):
            if self.tab_control.tab(i, "text") == f"ID: {phone_number_id}":
                return self.tab_control.nametowidget(self.tab_control.tabs()[i]).winfo_children()[0]
        return self.create_map_tab(phone_number_id)

    def update_map(self, phone_number_id, lat, lon):
        map_widget = self.get_map_widget(phone_number_id)

        # Initialize data structures if they don't exist
        if phone_number_id not in self.map_markers:
            self.map_markers[phone_number_id] = []
            self.polylines[phone_number_id] = None

        # Set the map position and zoom level
        map_widget.set_position(lat, lon)
        map_widget.set_zoom(15)

        # Add a marker to the map
        marker = map_widget.set_marker(lat, lon, text=f"ID: {phone_number_id}")
        self.map_markers[phone_number_id].append(marker)

        # Update the polyline
        self.update_polyline(phone_number_id)

        # Update the date label
        date = self.date_var.get()
        if phone_number_id in self.date_labels:
            self.date_labels[phone_number_id].config(text=f"Date: {date}")

        self.root.update_idletasks()

    def update_polyline(self, phone_number_id):
        map_widget = self.get_map_widget(phone_number_id)

        # Delete existing polyline if it exists
        if self.polylines[phone_number_id]:
            self.polylines[phone_number_id].delete()
            self.polylines[phone_number_id] = None

        # Create a list of (lat, lon) tuples from markers
        lat_lon_list = [
            (marker.position[0], marker.position[1]) for marker in self.map_markers[phone_number_id]
        ]

        # If there are at least two points, create a polyline
        if len(lat_lon_list) >= 2:
            self.polylines[phone_number_id] = map_widget.set_path(lat_lon_list)

    def clear_markers(self):
     phone_number_id = self.phone_number_var.get()
     if phone_number_id in self.map_markers:
        map_widget = self.get_map_widget(phone_number_id)

        # Delete regular markers
        for marker in self.map_markers[phone_number_id]:
            marker.delete()
        self.map_markers[phone_number_id].clear()

        # Delete polyline if it exists
        if self.polylines[phone_number_id]:
            self.polylines[phone_number_id].delete()
            self.polylines[phone_number_id] = None

        # Reset the map view
        map_widget.set_position(0, 0)
        map_widget.set_zoom(2)


    def navigate_to_latest_marker(self):
        phone_number_id = self.phone_number_var.get()
        if phone_number_id in self.map_markers and self.map_markers[phone_number_id]:
            latest_marker = self.map_markers[phone_number_id][-1]
            lat, lon = latest_marker.position  # Assuming 'position' is a tuple (lat, lon)
            map_widget = self.get_map_widget(phone_number_id)
            map_widget.set_position(lat, lon)
            map_widget.set_zoom(15)
        else:
            tk_messagebox.showinfo("No Markers", "No markers available to navigate to.")

    def calculate_distance(self):
     phone_number_id = self.phone_number_var.get()
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
        
        tk_messagebox.showinfo(
            "Total Distance",
            f"Total length of the polyline: {total_distance:.2f} km",
        )
     else:
        tk_messagebox.showinfo(
            "Insufficient Data", "At least two markers are needed to calculate the polyline length."
        )


    def show_route(self):
     phone_number_id = self.phone_number_var.get()
     date = self.date_var.get()
     if (
        phone_number_id
        and date
        and phone_number_id != "No data available"
        and date != "No data available"
     ):
        self.clear_markers()
        # Fetch coordinates with timestamps
        coordinates = self.db.get_coordinates_for_id_and_date(phone_number_id, date)
        if coordinates:
            for lat, lon, time_value in coordinates:
                self.update_map(phone_number_id, lat, lon)
                
            if phone_number_id in self.date_labels:
                self.date_labels[phone_number_id].config(text=f"Date: {date}")
        else:
            tk_messagebox.showinfo("No Data", "No data available for the selected date.")
            if phone_number_id in self.date_labels:
                self.date_labels[phone_number_id].config(text="Date: No data available")
     else:
        tk_messagebox.showinfo(
            "No Data",
            "No data available for the selected phone number and date.",
        )
        if phone_number_id in self.date_labels:
            self.date_labels[phone_number_id].config(text="Date: No data available")


    def update_phone_number_menu(self):
        phone_numbers_with_ids = self.db.get_all_phone_numbers_with_ids()
        if phone_numbers_with_ids:
            self.phone_number_var.set(phone_numbers_with_ids[0][0])
        else:
            self.phone_number_var.set("No data available")
        menu = self.phone_number_menu["menu"]
        menu.delete(0, "end")
        for phone_id, phone_number in phone_numbers_with_ids:
            menu.add_command(
                label=f"ID: {phone_id} ({phone_number})",
                command=lambda phone_id=phone_id: self.select_phone_number(phone_id),
            )
        self.update_date_menu()

    def update_date_menu(self):
     phone_number_id = self.phone_number_var.get()

    # Ensure the phone_number_id is valid and exists in the database
     if phone_number_id and phone_number_id != "No data available":
        dates = self.db.get_all_dates_for_number(phone_number_id)
     else:
        dates = []

    # Check if dates are available
     if dates:
        # Set the first available date as default
        self.date_var.set(dates[0])
     else:
        # If no dates are available, set the menu to "No data available"
        self.date_var.set("No data available")

    # Update the date menu options
     menu = self.date_menu["menu"]
     menu.delete(0, "end")

    # Add new dates to the menu
     for date in dates:
        menu.add_command(label=date, command=tk._setit(self.date_var, date))

    # Enable or disable the Show Route button based on date availability
     if not dates:
        self.show_route_button.config(state="disabled")
        if hasattr(self, 'date_labels') and phone_number_id in self.date_labels:
            self.date_labels[phone_number_id].config(text="No dates available")
     else:
        self.show_route_button.config(state="normal")
        if hasattr(self, 'date_labels') and phone_number_id in self.date_labels:
            self.date_labels[phone_number_id].config(text=f"Date: {dates[0]}")

    # Optionally log or display an update for debugging
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
                    # Iterate over the locations and enqueue each latitude and longitude
                    for lat, lon in locations:
                        self.sms_queue.put((phone_number, time_value, lat, lon))
                    
                    # After processing the SMS, delete all messages
                    self.serial_comm.delete_all_sms()


    def update_com_port_menu(self):
        # Get the list of available COM ports
        ports = serial.tools.list_ports.comports()
        com_ports = [port.device for port in ports]

        # Handle cases where no COM ports are available
        if com_ports:
            self.com_port_var.set(com_ports[0])
        else:
            self.com_port_var.set("No COM ports available")

        # Update the OptionMenu with the COM ports
        menu = self.com_port_menu["menu"]
        menu.delete(0, "end")

        # Add COM ports to the menu, or display a message if none are available
        if com_ports:
            for com_port in com_ports:
                menu.add_command(
                    label=com_port, command=lambda com_port=com_port: self.com_port_var.set(com_port)
                )
        else:
            menu.add_command(
                label="No COM ports available",
                command=lambda: self.com_port_var.set(""),
            )

    def connect_to_serial(self):
        com_port = self.com_port_var.get()
        if com_port and com_port != "No COM ports available":
            try:
                self.serial_comm = SerialCommunication(com_port)
                self.serial_comm.configure_for_sms()
                threading.Thread(target=self.wait_for_sms, daemon=True).start()
                self.connect_button.config(state="disabled")
                self.disconnect_button.config(state="normal")
                tk_messagebox.showinfo("Connected", "Serial Connection is established.")
            except Exception as e:
                tk_messagebox.showerror(
                    "Error",
                    f"Failed to connect to {com_port}. Ensure it is the correct port and try again.\n\nError: {e}",
                )
        else:
            tk_messagebox.showerror("Error", "No COM port selected or available.")

    def disconnect_serial(self):
        if self.serial_comm:
            try:
                self.serial_comm.serial_port.close()
                self.serial_comm = None
                self.connect_button.config(state="normal")
                self.disconnect_button.config(state="disabled")
                tk_messagebox.showinfo("Disconnected", "Serial connection closed.")
            except Exception as e:
                tk_messagebox.showerror(
                    "Error",
                    f"Failed to disconnect properly.\n\nError: {e}",
                )


if __name__ == "__main__":
    root = ThemedTk(theme="plastik")
    app = GPSMapApp(root)
    root.mainloop()
