from dotenv import load_dotenv
import os

load_dotenv()
 
ICS_URLS = os.getenv("ICS_URLS").split(',')
NOTION_TOKEN=os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
CATEGORY_ID = os.getenv("CATEGORY_ID")


SUBCATEGORIES = {
    "COSC262": os.getenv("SUBCATEGORIES_COSC262"),
    "COSC261": os.getenv("SUBCATEGORIES_COSC261"),
    "SENG201": os.getenv("SUBCATEGORIES_SENG201"),
    "EMTH210": os.getenv("SUBCATEGORIES_EMTH210"),
}
