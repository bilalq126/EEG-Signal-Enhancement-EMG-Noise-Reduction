#------------------------------------- DSP Project -----------------------------------------------------
#----------------------- EEG Signal Enhancement & EMG Noise Reduction ----------------------------------
#--------------------------------------- Made By -------------------------------------------------------
#-------------------------------- Bilal Qadeer (22-CP-30)-----------------------------------------------
#--------------------------------- Habib Khan (22-CP-62)------------------------------------------------
#--------------------------------  Rehan Umar (22-CP-72)------------------------------------------------
import tkinter as tk
from tkinter import filedialog, ttk
import numpy as np
import scipy.signal as signal
import pywt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pyedflib

# Globals
eeg_data = None
sampling_rate = None
channel_labels = None
selected_channel = 0
processed_signals = {}

# Function to load EEG data from .edf file
def load_data():
    global eeg_data, sampling_rate, channel_labels, selected_channel

    file_path = filedialog.askopenfilename(title="Select EEG Data File", filetypes=[("EDF Files", "*.edf")])
    if file_path:
        edf_reader = pyedflib.EdfReader(file_path)
        num_channels = edf_reader.signals_in_file
        channel_labels = edf_reader.getSignalLabels()
        sampling_rate = edf_reader.getSampleFrequency(0)  # Assume all channels have the same rate

        # Read all channel data
        eeg_data = [edf_reader.readSignal(i) for i in range(num_channels)]
        edf_reader.close()

        # Update channel selection dropdown
        channel_selector['values'] = channel_labels
        channel_selector.current(0)  # Default to first channel
        selected_channel = 0

        tk.messagebox.showinfo("File Loaded", f"EEG data loaded with {num_channels} channels.")
    else:
        tk.messagebox.showwarning("Warning", "No file selected!")

# Function to select channel
def select_channel(event):
    global selected_channel
    selected_channel = channel_selector.current()

# Function to calculate SNR
def calculate_snr(original, processed):
    signal_power = np.mean(original ** 2)
    noise_power = np.mean((original - processed) ** 2)
    snr = 10 * np.log10(signal_power / noise_power)
    return snr

# Function to filter data
def bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = signal.butter(order, [low, high], btype='band')
    return signal.filtfilt(b, a, data)

# Function to remove EMG noise using Wavelet Transform
def remove_emg(data):
    coeffs = pywt.wavedec(data, 'db4', level=5)  # Decompose signal
    threshold = np.median(np.abs(coeffs[-1])) / 0.6745  # Compute threshold
    denoised_coeffs = [pywt.threshold(c, threshold, mode='soft') for c in coeffs]  # Apply threshold
    return pywt.waverec(denoised_coeffs, 'db4')  # Reconstruct signal

# Function to enhance the signal (smoothing)
def enhance_signal(data):
    return signal.savgol_filter(data, 51, 3)

# Function to save the processed signal
def save_processed_signal():
    global processed_signals
    if not processed_signals:
        tk.messagebox.showerror("Error", "No processed signal available to save!")
        return

    file_path = filedialog.asksaveasfilename(
        title="Save Processed Signal",
        filetypes=[("Numpy Files", "*.npy")],
        defaultextension=".npy"
    )
    if file_path:
        np.save(file_path, processed_signals["enhanced"])
        tk.messagebox.showinfo("Save Successful", f"Processed signal saved to {file_path}")

# Function to process data and display results in GUI
def process_data():
    global eeg_data, selected_channel, sampling_rate, processed_signals

    if eeg_data is None:
        tk.messagebox.showerror("Error", "Please load EEG data first.")
        return

    # Retrieve user-set parameters
    low_cut = low_cut_slider.get()
    high_cut = high_cut_slider.get()
    window_length = int(window_length_slider.get())
    poly_order = int(poly_order_slider.get())

    # Ensure parameters are valid
    if low_cut >= high_cut:
        tk.messagebox.showerror("Error", "Low cut-off frequency must be less than high cut-off frequency.")
        return
    if window_length % 2 == 0 or window_length <= poly_order:
        tk.messagebox.showerror("Error", "Window length must be odd and greater than polynomial order.")
        return

    original = eeg_data[selected_channel]
    filtered = bandpass_filter(original, low_cut, high_cut, sampling_rate)
    denoised = remove_emg(filtered)
    enhanced = signal.savgol_filter(denoised, window_length, poly_order)

    # Save processed signals globally
    processed_signals = {
        "original": original,
        "filtered": filtered,
        "denoised": denoised,
        "enhanced": enhanced,
    }

    # Calculate SNR
    snr_filtered = calculate_snr(original, filtered)
    snr_denoised = calculate_snr(original, denoised)
    snr_enhanced = calculate_snr(original, enhanced)

    # Update SNR values in the GUI
    snr_label['text'] = (
        f"SNR (Filtered): {snr_filtered:.2f} dB\n"
        f"SNR (Denoised): {snr_denoised:.2f} dB\n"
        f"SNR (Enhanced): {snr_enhanced:.2f} dB"
    )

    # Plot results inside the Tkinter window
    fig = Figure(figsize=(10, 6), dpi=100)
    fig.subplots_adjust(hspace=0.6)  # Add vertical spacing between subplots
    ax1 = fig.add_subplot(4, 1, 1)
    ax1.plot(original, label='Original Signal')
    ax1.legend(loc='upper right')
    ax1.set_title("Original Signal")

    ax2 = fig.add_subplot(4, 1, 2)
    ax2.plot(filtered, label='Filtered Signal', color='blue')
    ax2.legend(loc='upper right')
    ax2.set_title("Filtered Signal")

    ax3 = fig.add_subplot(4, 1, 3)
    ax3.plot(denoised, label='Denoised Signal', color='orange')
    ax3.legend(loc='upper right')
    ax3.set_title("Denoised Signal")

    ax4 = fig.add_subplot(4, 1, 4)
    ax4.plot(enhanced, label='Enhanced Signal', color='green')
    ax4.legend(loc='upper right')
    ax4.set_title("Enhanced Signal")

    # Clear previous canvas and embed new plot
    for widget in plot_frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# GUI Setup
root = tk.Tk()
root.state('zoomed')  # Start in full screen (for Windows/Linux)
root.title("EEG Signal Enhancement and EMG Noise Reduction")
root.geometry("1200x700")  # Larger window for split layout
root.configure(bg="#2c3e50")  # Dark background

# Create frames for layout
control_frame = tk.Frame(root, width=300, padx=10, pady=10, bg="#34495e")
control_frame.grid(row=0, column=0, sticky="ns")
plot_frame = tk.Frame(root, padx=10, pady=10, bg="#2c3e50")
plot_frame.grid(row=0, column=1, sticky="nsew")

# Configure row/column weights for resizing
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

# Load data button
load_button = tk.Button(control_frame, text="Load EEG Data", command=load_data, bg="#16a085", fg="white")
load_button.pack(pady=10, fill=tk.X)

# Channel selection dropdown
channel_selector_label = tk.Label(control_frame, text="Select Channel:", bg="#34495e", fg="white")
channel_selector_label.pack()
channel_selector = ttk.Combobox(control_frame, state="readonly")
channel_selector.bind("<<ComboboxSelected>>", select_channel)
channel_selector.pack(pady=5, fill=tk.X)

# Process button
process_button = tk.Button(control_frame, text="Process EEG Data", command=process_data, bg="#16a085", fg="white")
process_button.pack(pady=10, fill=tk.X)

# Save button
save_button = tk.Button(control_frame, text="Save Processed Signal", command=save_processed_signal, bg="#e67e22", fg="white")
save_button.pack(pady=10, fill=tk.X)

# SNR display
snr_label = tk.Label(control_frame, text="SNR Values: ", justify="left", font=("Arial", 12), bg="#34495e", fg="white")
snr_label.pack(pady=10, fill=tk.X)

# Frequency range labels and sliders
filter_label = tk.Label(control_frame, text="Bandpass Filter Settings:", bg="#34495e", fg="white", font=("Arial", 12))
filter_label.pack(pady=(20, 5), anchor="w")

low_cut_label = tk.Label(control_frame, text="Low Cut-off Frequency (Hz):", bg="#34495e", fg="white")
low_cut_label.pack(anchor="w")
low_cut_slider = tk.Scale(control_frame, from_=0.1, to=100, resolution=0.1, orient="horizontal", bg="#34495e", fg="white")
low_cut_slider.set(0.5)  # Default value
low_cut_slider.pack(fill=tk.X, pady=5)

high_cut_label = tk.Label(control_frame, text="High Cut-off Frequency (Hz):", bg="#34495e", fg="white")
high_cut_label.pack(anchor="w")
high_cut_slider = tk.Scale(control_frame, from_=0.1, to=100, resolution=0.1, orient="horizontal", bg="#34495e", fg="white")
high_cut_slider.set(50)  # Default value
high_cut_slider.pack(fill=tk.X, pady=5)

# Smoothing settings
smoothing_label = tk.Label(control_frame, text="Smoothing (Savitzky-Golay) Settings:", bg="#34495e", fg="white", font=("Arial", 12))
smoothing_label.pack(pady=(20, 5), anchor="w")

window_length_label = tk.Label(control_frame, text="Window Length:", bg="#34495e", fg="white")
window_length_label.pack(anchor="w")
window_length_slider = tk.Scale(control_frame, from_=5, to=101, resolution=2, orient="horizontal", bg="#34495e", fg="white")
window_length_slider.set(51)  # Default value
window_length_slider.pack(fill=tk.X, pady=5)

poly_order_label = tk.Label(control_frame, text="Polynomial Order:", bg="#34495e", fg="white")
poly_order_label.pack(anchor="w")
poly_order_slider = tk.Scale(control_frame, from_=1, to=5, resolution=1, orient="horizontal", bg="#34495e", fg="white")
poly_order_slider.set(3)  # Default value
poly_order_slider.pack(fill=tk.X, pady=5)

root.mainloop()

#------------------------------------- DSP Project -----------------------------------------------------
#----------------------- EEG Signal Enhancement & EMG Noise Reduction ----------------------------------
#--------------------------------------- Made By -------------------------------------------------------
#-------------------------------- Bilal Qadeer (22-CP-30)-----------------------------------------------
#--------------------------------- Habib Khan (22-CP-62)------------------------------------------------
#--------------------------------  Rehan Umar (22-CP-72)------------------------------------------------