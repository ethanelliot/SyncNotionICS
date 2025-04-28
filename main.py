"""
made by: @ethan elliot
Date: 1/03/24
"""

import re
from ics import Calendar, Event
import requests
from notion_client import Client
import constants
import logging
from datetime import datetime


logging.basicConfig(level=logging.INFO)
notion = Client(auth=constants.NOTION_TOKEN, log_level=logging.ERROR)


def get_calender_events() -> Calendar:
    merged_cal = Calendar()
    for url in constants.ICS_URLS:
        logging.info(f"Getting ics from {url}")
        resp = requests.get(url)
        cal = Calendar(resp.text)
        merged_cal.events.update(cal.events)
        logging.info(f"Successfully added events to merged calendar")
    return merged_cal


def find_class_code(categories: set[str]):
    pattern = r"^[A-Za-z]{4}\d{3}-(\d{2}|\d{4})S\d$"
    class_code = next((c for c in categories if re.match(pattern, c)), "")
    # format class code
    class_code = class_code.split("-")[0]
    return class_code


def format_name(name: str) -> str:

    pattern = re.compile(r'^(?:Quiz\s*)?(\d+)[^\w]*(.*)', re.IGNORECASE)

    match = pattern.match(name)
    if not match:
        return name.removesuffix("closes")

    quiz_number = int(match.group(1)) 
    remaining_text = match.group(2).strip().removesuffix("closes") 


    return f"Quiz {quiz_number} – {remaining_text}"


def format_event(event: Event) -> dict:
    return {
        "uid": event.uid,
        "name": format_name(event.name),
        "end_date": event.end.datetime,
        "class": find_class_code(event.categories),
    }


def get_upcoming_page_events() -> None:
    current_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # query notion to get events after today
    response = notion.databases.query(
        database_id=constants.NOTION_DATABASE_ID,
        filter={
            "property": "End Date",
            "date": {"after": current_datetime.isoformat()},
        },
    )
    # Make dict where key = ics_uid and value = {id: notion id, end_date: end date from notion db}
    page_events = {}
    for page_event in response.get("results"):
        properties = page_event.get("properties", {})
        id = page_event.get("id")

        end_date = properties.get("End Date", {})
        end_date = end_date.get("date", {})
        end_date = end_date.get("start", None)

        ics_uid = properties.get("ics_uid", {})
        ics_uid = ics_uid.get("rich_text", [])
        ics_uid = next(iter(ics_uid), {})
        ics_uid = ics_uid.get("plain_text", "")

        page_events.setdefault(
            ics_uid,
            {"id": id, "end_date": datetime.fromisoformat(end_date)},
        )

    return page_events


def handle_events(cal: Calendar) -> list[dict]:
    new = []
    updates = []

    #get all events from notion
    upcoming_page_events = get_upcoming_page_events()

    for event in cal.events:
        event = format_event(event)
        event_uid = event.get("uid", None)

        # filerting events

        # we only want to add events for when events close
        if name := event.get("name"):
            if name.endswith("opens"):
                continue

        if event["class"] not in constants.SUBCATEGORIES.keys():
            continue

        # filter events that have already been recorded in the db
        # if they have but the date is different we will update them
        if upcoming_page_event := upcoming_page_events.get(event_uid, False):
            # will always have end date as this is derived from ics format
            if upcoming_page_event.get('end_date') == event.get("end_date"):
                continue

            updates.append(
                {
                    **event,
                    "notion_id": upcoming_page_event["id"],
                }
            )
            continue

        new.append(event)
    return new, updates


def upload_events_to_notion(events: dict) -> None:
    for event in events:
        logging.info("Adding event: %s due=%s",event['name'] ,event['end_date'].strftime("%A, %B %d, %Y at %I:%M %p"))
        notion.pages.create(
            parent={"database_id": constants.NOTION_DATABASE_ID},
            properties={
                "Category": {
                    "relation": [{"id": constants.CATEGORY_ID}],
                    "has_more": False,
                },
                "Subcategory": {
                    "type": "relation",
                    "relation": [{"id": constants.SUBCATEGORIES[event["class"]]}],
                    "has_more": False,
                },
                "ics_uid": {
                    "type": "rich_text",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": event["uid"],
                            },
                        }
                    ],
                },
                "End Date": {
                    "type": "date",
                    "date": {
                        "start": event["end_date"].isoformat(),
                    },
                },
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": event["name"],
                            },
                        }
                    ],
                },
            },
        )


def update_events_in_notion(updates: dict) -> None:
    for update in updates:
        logging.info("Updating event: %s due=%s (Notion page id=%s)",update['name'],update['end_date'].strftime("%A, %B %d, %Y at %I:%M %p"),update["notion_id"])
        notion.pages.update(
            page_id=update["notion_id"],
            properties={
                "End Date": {
                    "type": "date",
                    "date": {
                        "start": update["end_date"].isoformat(),
                    },
                },
                "Name": {
                    "id": "title",
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": update["name"],
                            },
                        }
                    ],
                },
            },
        )


def main():
    cal = get_calender_events()

    new, updates = handle_events(cal)

    upload_events_to_notion(new)
    update_events_in_notion(updates)
    logging.info('All events created and updates')


if __name__ == "__main__":
    main()
