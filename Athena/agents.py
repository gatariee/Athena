import requests
from Athena.types import Agent

def update_beacons(url: str, listener: str = "http") -> list[Agent]:
    """
    Update the list of agents from a Winton listener (default: HTTP)

    Args:
        url (str): URL of the listener (e.g http://127.0.0.1:80)
        listener (str, optional): Type of listener. Defaults to "http".

    Returns:
        list[Agent]: List of agents
    """
    try:
        match listener:
            case "http":
                res = requests.get(f"{url}/agents")
                if res.status_code == 200:
                    return res.json()["agents"]
                else:
                    return [] # Teamserver broke, but is alive.
            case _:
                return [] # unknown listener
    except requests.exceptions.ConnectionError:
        print(f"[!] Failed to connect to {url} [ConnectionError]")
        return [] # Teamserver is down, log to console and continue.