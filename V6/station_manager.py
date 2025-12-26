import logging

log = logging.getLogger(__name__)

# Define station names
PACKING = 'packing'
SCHEDULING = 'scheduling'
SHIPPING = 'shipping'
NOTIFICATION = 'notification'

# Define status colors
COLOR_GREY = 'grey'
COLOR_GREEN = 'green'
COLOR_ORANGE = 'orange'
COLOR_RED = 'red'
COLOR_YELLOW = 'yellow'

# Initialize the status of all stations
_station_statuses = {
    PACKING: COLOR_GREY,
    SCHEDULING: COLOR_GREY,
    SHIPPING: COLOR_GREY,
    NOTIFICATION: COLOR_GREY,
}

_listeners = []

def _notify_listeners():
    """Notify all registered listeners of a status change."""
    for listener in _listeners:
        try:
            listener()
        except Exception as e:
            log.error(f"Error notifying a station status listener: {e}", exc_info=True)

def add_listener(listener_func):
    """Add a listener function to be called on status changes."""
    if listener_func not in _listeners:
        _listeners.append(listener_func)
        log.debug(f"Added station status listener: {listener_func.__name__}")

def remove_listener(listener_func):
    """Remove a listener function."""
    if listener_func in _listeners:
        _listeners.remove(listener_func)
        log.debug(f"Removed station status listener: {listener_func.__name__}")

def set_status(station, color):
    """
    Sets the status (color) for a given station.
    
    Args:
        station (str): The name of the station (e.g., PACKING).
        color (str): The color to set (e.g., COLOR_GREEN).
    """
    if station in _station_statuses:
        if _station_statuses[station] != color:
            _station_statuses[station] = color
            log.info(f"Station '{station}' status changed to '{color}'.")
            _notify_listeners()
    else:
        log.warning(f"Attempted to set status for unknown station: {station}")

def get_status(station):
    """
    Gets the current status (color) of a given station.
    
    Args:
        station (str): The name of the station.
        
    Returns:
        str: The current color status, or COLOR_GREY if station is unknown.
    """
    return _station_statuses.get(station, COLOR_GREY)

def get_all_statuses():
    """Returns a copy of the statuses of all stations."""
    return _station_statuses.copy()
