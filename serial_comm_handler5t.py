import serial
import time
import re
from datetime import datetime, timedelta

class SerialCommunication:
    def __init__(self, port):
        self.serial_port = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=5
        )

    def configure_for_sms(self):
        self.send_command('AT+CNMI=2,1,0,0,0')

    def send_command(self, command):
        self.serial_port.write((command + '\r').encode())
        time.sleep(1)
        response = self.serial_port.read(self.serial_port.in_waiting).decode()
        print(f"Sent: {command}, Received: {response}")  # Debugging
        return response

    def increment_timestamps(self, initial_timestamp, count):
        """
        Increment the timestamps by 1 minute starting from the initial timestamp.

        Args:
            initial_timestamp (str): The initial timestamp in HH:MM:SS format.
            count (int): The number of timestamps to generate.

        Returns:
            list: A list of incremented timestamps.
        """
        timestamps = []
        ts = datetime.strptime(initial_timestamp, "%H:%M:%S")
        for i in range(count):
            incremented_ts = ts + timedelta(minutes=i)
            timestamps.append(incremented_ts.strftime("%H:%M:%S"))
        return timestamps

    def parse_message(self, message):
        """
        Parse the plaintext message to extract time and coordinates.

        Args:
            message (str): The plaintext message in the format "HH:MM:SS; lat,lon; lat,lon; ..."

        Returns:
            tuple: (time_value, coords) where coords is a list of (lat, lon) tuples.
        """
        try:
            message = message.strip()
            parts = message.split(';')
            time_value = parts[0].strip()  # Extract time
            coords = []

            for coord in parts[1:]:
                coord = coord.strip()  # Remove extra spaces
                try:
                    lat, lon = map(float, coord.split(','))
                    if lat != 0.0 and lon != 0.0:
                        coords.append((lat, lon))
                except ValueError:
                    print(f"Skipping invalid coordinate: {coord}")

            return time_value, coords
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None, []

    def read_sms(self, index):
        command = f'AT+CMGR={index}'
        response = self.send_command(command)
        print(f"Read SMS response: {response}")  # Debugging

        match = re.search(r'\+CMGR: "REC UNREAD","(\+?\d+)".*\r\n(.+)\r\n', response)
        if match:
            phone_number = match.group(1)
            message_body = match.group(2).strip()
            print(f"Extracted message body: {message_body}")  # Debugging

            # Parse the message
            time_value, coords = self.parse_message(message_body)

            if time_value and coords:
                # Increment timestamps for each coordinate
                timestamps = self.increment_timestamps(time_value, len(coords))
                coords_with_timestamps = [(lat, lon, ts) for (lat, lon), ts in zip(coords, timestamps)]
                return phone_number, coords_with_timestamps

        return None, []

    def delete_all_sms(self):
        # Send the command to delete all SMS from the SIM card
        response = self.send_command('AT+CMGD=1,4')
        if "OK" in response:
            print("All SMS messages deleted successfully.")
        else:
            print("Failed to delete SMS messages.")