
import heapq
from datetime import datetime


def prioritize_donations(donations):

    # Create an empty min heap
    priority_queue = []

    # Get the current date and time
    current_time = datetime.now()

    # Add donations to the heap
    for donation in donations:

        # Convert expiry time from string to datetime
        expiry = datetime.fromisoformat(donation["expiry_time"])

        # Ignore donations whose deadlines have passed
        if expiry <= current_time:
            continue

        # Insert donation into the min heap
        heapq.heappush(
            priority_queue,
            (
                expiry.timestamp(),
                donation["donation_id"],
                donation
            )
        )

    # Extract donations in priority order
    prioritized = []

    while priority_queue:
        item = heapq.heappop(priority_queue)
        prioritized.append(item[2])

    return prioritized
