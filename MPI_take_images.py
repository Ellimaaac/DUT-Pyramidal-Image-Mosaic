import math
import time
from pathlib import Path
import pyvisa as visa

# ==============================
# User config
# ==============================
SNAPSHOT_DIR = Path(r"D:\USER\FOLDER")
GPIB_BOARD = "GPIB0"
GPIB_ADDRESS = 13
IMAGE_TYPE = ".jpeg"
SNAPSHOT_DELAY_SECONDS = 1        # Delay after moving the chuck before taking the snapshot.
MOVE_SETTLE_SECONDS = 0.5           # Delay after each chuck move to let the mechanics settle.
SCAN_MODE = "rectangle"                # Scan mode: "circle" or "rectangle".
# ==============================
# Rectangular scan 
# ==============================
RECTANGLE_X_START_UM = 298128
RECTANGLE_X_END_UM = 275487
RECTANGLE_Y_START_UM = -24799
RECTANGLE_Y_END_UM = -9218
# ==============================
# Circular scan config
# ==============================
WAFER_CENTER_X_UM = 162663          # Chuck coordinates of the wafer center, in micrometers.
WAFER_CENTER_Y_UM = -161247
WAFER_EDGE_X_UM = 162663
WAFER_EDGE_Y_UM = -311000
EDGE_MARGIN_UM = 2000               # add an extra distance to avoid cropped wafer
# ==============================
# Step scan 
# ==============================
X_STEP_UM = 1000
Y_STEP_UM = 800
# ==============================
# Save config - if GPIB or else break
# ==============================
SAVE_ENABLED = False
# Last already-saved position. Example: position from snapshot_6649.
SAVE_X_UM = 219915
SAVE_Y_UM = -271600
SAVE_TOLERANCE_UM = 100             # SAVE tolerance, in micrometers.
# False: SAVE after the reference position.
# True: include the reference position again.
RETAKE_SAVE_POSITION = False
# First snapshot index to write.
# Example: if the last file is snapshot_6649, set this to 6650.
START_SNAPSHOT_INDEX = 1

# ==============================
# Instrument functions²
# ==============================
def send_command(instrument, command: str) -> str:
    """Send a GPIB command and return the useful part of the reply."""
    instrument.clear()
    reply = instrument.query(command)
    reply = reply.strip()
    # reply = "0,OK,162663.0,-161247.0"
    #
    # reply_parts = [
    #     "0",
    #     "OK",
    #     "162663.0,-161247.0"
    # ]
    tmp = reply.split(",", 2) 
    if len(tmp) != 3:
        message = f"Unexpected GPIB reply for command '{command}': {reply}"
        raise RuntimeError(message)
    error_code = tmp[0].strip()
    coordinates = tmp[2].strip()
    if error_code != "0":
        print(f"[GPIB ERROR] {command} -> {reply}")
    return coordinates

def read_chuck_position(instrument) -> tuple[float, float]:
    """Read the current chuck X/Y position in micrometers."""
    payload = send_command(instrument, "get_chuck_xy")
    if not payload:
        raise RuntimeError("get_chuck_xy failed: empty payload")
    x_text, y_text = payload.split(",")
    return float(x_text), float(y_text)

def move_chuck_to(instrument, x_um: float, y_um: float, debug=False) -> None:
    """Move the chuck to the next X/Y position."""
    if debug :print(f"Moving chuck to X={x_um:.1f} um, Y={y_um:.1f} um")
    send_command(instrument, f"move_chuck_xy zero,{x_um:.1f},{y_um:.1f}")
    time.sleep(MOVE_SETTLE_SECONDS)

def save_snapshot(instrument, snapshot_index: int, x_um: float, y_um: float, z_um: float, debug =False) -> Path:
    """Save one snapshot using the current chuck position."""
    def coordinate_token(value: float) -> str: # float to text for image name
        return f"{value:.1f}".replace(".", "p")
    filename = (
        f"snapshot_{snapshot_index}_"
        f"coordonneeXduchuck_{coordinate_token(x_um)}_"
        f"coordonneeYduchuck_{coordinate_token(y_um)}_"
        f"coordonneeZautoFocus_{coordinate_token(z_um)}"
        f"{IMAGE_TYPE}"
    )
    snapshot_path = SNAPSHOT_DIR / filename
    send_command(instrument, f'vis:snap_image "{snapshot_path}", 0')
    if debug :print(f"Saved: {snapshot_path}")
    return snapshot_path

def scan_position(instrument, snapshot_index: int, x_um: float, y_um: float, autofocus=False) -> int:
    """Move to scan position and save snapshot."""
    move_chuck_to(instrument, x_um, y_um)
    actual_x_um, actual_y_um = read_chuck_position(instrument)
    # Autofocus is currently disabled. Replace this value with the autofocus command result. if i found where is the autofocus command
    if autofocus: 
        print("Need to find the autofocus function")
        z_raw = send_command(instrument, f"vis:auto_focus Calibration")
        try:
            actual_z_um = float(z_raw.split(",")[0].strip())
        except ValueError:
            print(f"Could not parse z value {actual_z_um}, defaulting to 0")
            actual_z_um=0
    else: 
        actual_z_um = 0
    time.sleep(SNAPSHOT_DELAY_SECONDS)
    save_snapshot(instrument=instrument,snapshot_index=snapshot_index,x_um=actual_x_um,y_um=actual_y_um,z_um=actual_z_um,)
    return snapshot_index + 1

# ==============================
# Scan logic
# ==============================
def run_rectangular_scan(instrument) -> None:
    """Run a rectangular scan."""
    x_start = RECTANGLE_X_START_UM
    x_end = RECTANGLE_X_END_UM
    y_start = RECTANGLE_Y_START_UM
    y_end = RECTANGLE_Y_END_UM
    x_step = math.copysign(abs(X_STEP_UM), x_end - x_start)     # If the end is larger than the beginning, the step size is positive.
    y_step = math.copysign(abs(Y_STEP_UM), y_end - y_start)     # If the end is smaller than the beginning, the step size is negative.
    print("Rectangular scan enabled.")
    print(f"Scan X: {x_start:.1f} -> {x_end:.1f} step {x_step:.1f} um")
    print(f"Scan Y: {y_start:.1f} -> {y_end:.1f} step {y_step:.1f} um")
    snapshot_index = START_SNAPSHOT_INDEX # Fisrt snapshot
    y_um = y_start # First ligne
    while (y_um - (y_end + y_step)) * y_step <= 1e-6: # To be sure I cover the edges, I add one step
        x_um = x_start
        while (x_um - (x_end+x_step)) * x_step <= 1e-6:
            snapshot_index = scan_position(instrument, snapshot_index, x_um, y_um)
            x_um += x_step
        y_um += y_step
    print("Rectangular scan completed.")

def run_circular_scan(instrument, debug=False) -> None:
    """Run a circular wafer scan with optional save support."""
    center_x_um = WAFER_CENTER_X_UM
    center_y_um = WAFER_CENTER_Y_UM
    x_step_um = abs(X_STEP_UM)
    y_step_um = abs(Y_STEP_UM)
    wafer_radius_um = math.hypot(WAFER_EDGE_X_UM - center_x_um, WAFER_EDGE_Y_UM - center_y_um)
    # scan_radius_um = wafer_radius_um + EDGE_MARGIN_UM - max(x_step_um, y_step_um)
    scan_radius_um = wafer_radius_um + EDGE_MARGIN_UM
    if wafer_radius_um <= 0:
        raise RuntimeError("Invalid wafer radius. Check center and edge coordinates.")
    if scan_radius_um <= 0:
        raise RuntimeError(
            "Invalid scan radius: wafer radius + edge margin <= 0. "
            f"radius={wafer_radius_um:.1f}, margin={EDGE_MARGIN_UM:.1f}, "
            f"step={max(x_step_um, y_step_um):.1f}"
        )
    if debug:print("Circular scan enabled.")
    if debug:print(f"Center:      X={center_x_um:.1f} um, Y={center_y_um:.1f} um")
    if debug:print(f"Edge point:  X={WAFER_EDGE_X_UM:.1f} um, Y={WAFER_EDGE_Y_UM:.1f} um")
    if debug:print(f"Radius:      {wafer_radius_um:.1f} um")
    if debug:print(f"Edge margin: {EDGE_MARGIN_UM:.1f} um")
    if debug:print(f"Safe radius: {scan_radius_um:.1f} um")
    if debug:print(f"Step:        dx={x_step_um:.1f} um, dy={y_step_um:.1f} um")
    if debug:print(f"Start index: {START_SNAPSHOT_INDEX}")

    if SAVE_ENABLED:
        print("SAVE enabled.")
        print(f"SAVE reference: X={SAVE_X_UM:.1f} um, Y={SAVE_Y_UM:.1f} um")
        print(f"SAVE tolerance: {SAVE_TOLERANCE_UM:.1f} um")
        print(f"Retake SAVE position: {RETAKE_SAVE_POSITION}")
        # Keep the scan grid aligned with the last known saved point. Use the last image coordinates
        x_grid_origin_um = SAVE_X_UM
        y_grid_origin_um = SAVE_Y_UM
    else:
        if debug:print("SAVE disabled. Scan will start from the beginning.")
        # Without SAVE, align the grid on the wafer center.
        x_grid_origin_um = center_x_um
        y_grid_origin_um = center_y_um

    def next_grid_value(value_um: float, origin_um: float, step_um: float) -> float:
        """Return the first grid point greater than or equal to value_um."""
        # Compute how many steps are needed from the grid origin to reach value_um.
        # math.ceil() rounds up so the returned point is never before value_um.
        # If Grid positions are: 0, 1000, 2000, 3000. The first grid position >= 2300 is 3000.
        return origin_um + math.ceil((value_um - origin_um) / step_um) * step_um

    def is_inside_scan_area(x_um: float, y_um: float) -> bool:
        """Return True when the point is inside the circular scan area."""
        return (x_um - center_x_um) ** 2 + (y_um - center_y_um) ** 2 <= scan_radius_um**2

    snapshot_index = START_SNAPSHOT_INDEX
    skipped_points = 0
    captured_points = 0

    # if reached is enabled, we must first locate the SAVE_X_UM / SAVE_Y_UM point.
    # if reached is disabled, we can scan directly.
    SAVE_reached = not SAVE_ENABLED

    min_y_um = center_y_um - scan_radius_um
    max_y_um = center_y_um + scan_radius_um
    y_um = next_grid_value(min_y_um, y_grid_origin_um, y_step_um) # to be on the grid

    while y_um <= max_y_um + 1e-6:
        y_offset_um = y_um - center_y_um
        if abs(y_offset_um) > scan_radius_um: # if Y is out the cercle, skip the line
            y_um += y_step_um                 # Normally, this should never happen 
            continue                          # since y_um is already between min_y_um and 
                                              # max_y_um, but it protects against rounding.
                                              
        # This line calculates the X length for a given Y line, while staying within the circle.
        # In the center of the wafer, the X line is very wide. Near the top or bottom of the wafer, 
        # the X line is short.
        # Cercle equation : x²+y²=radius² so, x=sqrt(radius²-y²)
        x_half_width_um = math.sqrt(max(0.0, scan_radius_um**2 - y_offset_um**2))
        # min_x_um = center_x_um - x_half_width_um + x_step_um
        # max_x_um = center_x_um + x_half_width_um - x_step_um
        min_x_um = center_x_um - x_half_width_um 
        max_x_um = center_x_um + x_half_width_um 
        if min_x_um > max_x_um: # no X point scan 
            y_um += y_step_um
            continue
        #chooses the first X point aligned on the grid that is greater than or equal to min_x_um
        #start at the next valid grid point
        x_um = next_grid_value(min_x_um, x_grid_origin_um, x_step_um)
        if debug:print(f"Row Y={y_um:.1f} um: X from {x_um:.1f} to {max_x_um:.1f}")
        while x_um <= max_x_um + 1e-6:
            if not is_inside_scan_area(x_um, y_um): # Even though min_x_um and max_x_um have 
                x_um += x_step_um                   # been calculated to stay within the circle,  
                continue                            # this condition is still verified.
            # This section is used to resume the scan after an interruption.
            # It skips all points that were already scanned before the saved position.
            if SAVE_ENABLED and not SAVE_reached:
                # return bools: Should this point be skipped? and Have we reached the saved position?
                should_skip, SAVE_reached = should_skip_for_SAVE(x_um, y_um) 
                if should_skip:
                    skipped_points += 1
                    x_um += x_step_um
                    continue
            snapshot_index = scan_position(instrument, snapshot_index, x_um, y_um)
            captured_points += 1
            x_um += x_step_um
        y_um += y_step_um
    # If the recovery/resume position was never found
    if SAVE_ENABLED and not SAVE_reached:
        print("WARNING: Save area was not reached.")
        print("Check SAVE_X_UM, SAVE_Y_UM, SAVE_TOLERANCE_UM, X_STEP_UM, Y_STEP_UM.")
        print("No images were taken after the SAVE position because it was not reached.")
    print("Circular scan completed.")
    if debug:print(f"Images taken: {captured_points}")
    if debug:print(f"Points skipped before SAVE: {skipped_points}")

def should_skip_for_SAVE(x_um: float, y_um: float, debug=False) -> tuple[bool, bool]:
    """
    Decide whether a point must be skipped while looking for the SAVE position.
    Returns:
        should_skip: True when the current point is before the SAVE target.
        SAVE_reached: True once scanning can restart from the current row/point.
    """
    # Case 1 : we are before the saved line. The current Y line is still before the line where we need to resume.
    if y_um < SAVE_Y_UM - SAVE_TOLERANCE_UM:
        # True  -> skip the point
        # False -> The save position has not yet been reached
        return True, False
    # Case 2 : we are on the saved line. The current Y-line is quite close to the saved line.
    # A tolerance is used because the coordinates may be slightly different.
    if abs(y_um - SAVE_Y_UM) <= SAVE_TOLERANCE_UM:
        # we want to restore the saved point
        if RETAKE_SAVE_POSITION:
            # If True, then the scan resumes from the saved point, so it retakes this image.
            if x_um < SAVE_X_UM - SAVE_TOLERANCE_UM: # As long as x_um is before the saved point, we skip the point
                return True, False
            if debug:print(f"Save reached near reference. Starting at X={x_um:.1f}, Y={y_um:.1f}")
            return False, True
        # we don't want to retake the saved point
        if x_um <= SAVE_X_UM + SAVE_TOLERANCE_UM: # As long as we are at the saved point or before, skip
            return True, False
        if debug: print(f"Save reached after reference point. Starting at X={x_um:.1f}, Y={y_um:.1f}")
        return False, True
    # we have already passed the saved line.
    # we start again at the first available point of this new line.
    if y_um > SAVE_Y_UM + SAVE_TOLERANCE_UM:
        if debug:print(f"Save Y passed. Starting at first available point X={x_um:.1f}, Y={y_um:.1f}")
        return False, True
    # default case
    return True, False

# ==============================
# Main 
# ==============================
def main(debug=False):
    resource_manager = None
    instrument = None
    initial_x_um = None
    initial_y_um = None
    try:
        resource_manager = visa.ResourceManager()
        instrument = resource_manager.open_resource(f"{GPIB_BOARD}::{GPIB_ADDRESS}::INSTR")
        instrument.write_termination = "\n"
        instrument.read_termination = "\n"
        instrument.timeout = 30000
        instrument.clear()

        if debug:print("IDN:", instrument.query("*IDN?").strip())
        send_command(instrument, f"vis:switch_camera Scope")
        initial_x_um, initial_y_um = read_chuck_position(instrument)
        if debug:print(f"Initial chuck XY: X={initial_x_um:.1f} um, Y={initial_y_um:.1f} um")
        scan_mode = SCAN_MODE.lower().strip()
        if scan_mode == "circle":
            run_circular_scan(instrument)
        elif scan_mode == "rectangle":
            run_rectangular_scan(instrument)
        else:
            raise RuntimeError(f"Unknown SCAN_MODE={SCAN_MODE!r}. Use 'circle' or 'rectangle'.")
        print("Scan completed.")
    except KeyboardInterrupt:
        print("\nInterrupted by user with Ctrl+C.")
    except Exception as exc:
        print("Error:", type(exc).__name__, exc)
    finally:
        if instrument is not None:
            if initial_x_um is not None and initial_y_um is not None:
                try:
                    print(f"Returning to initial position: X={initial_x_um:.1f} um, Y={initial_y_um:.1f} um")
                    move_chuck_to(instrument, initial_x_um, initial_y_um)
                except Exception as exc:
                    print("Return move failed:", type(exc).__name__, exc)
            try:
                instrument.close()
            except Exception as exc:
                print("Instrument close failed:", type(exc).__name__, exc)
        if resource_manager is not None:
            try:
                resource_manager.close()
            except Exception as exc:
                print("Resource manager close failed:", type(exc).__name__, exc)
        print("Closed GPIB session. Done.")
        
if __name__ == "__main__":
    main()
