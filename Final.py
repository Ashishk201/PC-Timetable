from flask import Flask, render_template_string, request
import threading
import time
import pandas as pd

# --- Selenium, BeautifulSoup, and Google Sheets related imports ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

# Google Sheets Imports
import gspread
from google.oauth2.service_account import Credentials

# --- Flask App Setup ---
app = Flask(__name__)

# HTML template with a button and a placeholder for output.
HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Web Scraper and Updater</title>
</head>
<body>
    <h1>Run Web Scraping & Update Process</h1>
    <form method="post">
        <button type="submit">Run Process</button>
    </form>
    {% if output %}
    <h2>Output:</h2>
    <pre>{{ output }}</pre>
    {% endif %}
</body>
</html>
"""

# Define a function that combines the code from webscrapper.py and updation.py.
def run_process():
    output_lines = []
    try:
        # --- Web Scraping Section (from WebScrapper.py) ---
        output_lines.append("Starting Selenium WebDriver...")
        # You might need to set the executable path or use a webdriver manager.
        driver = webdriver.Chrome()
        driver.get("https://srcccollegetimetable.in//login.php")
        time.sleep(2)
        
        # Login using provided credentials.
        USERNAME, PASSWORD = "placement", "250505"
        search_box = driver.find_element(By.NAME, "username")
        search_box.send_keys(USERNAME)
        password_box = driver.find_element(By.NAME, "pass")
        password_box.send_keys(PASSWORD)
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)
        
        output_lines.append("Logged in successfully.")
        
        # Click on the Room button.
        Room_button = driver.find_element(By.XPATH, "/html/body/table/tbody/tr[3]/td/div")
        Room_button.click()
        time.sleep(2)
        
        # Parse page source using BeautifulSoup.
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        if table is None:
            output_lines.append("No table found on the page!")
            driver.quit()
            return "\n".join(output_lines)
        
        # Extract headers
        headers = [th.text.strip() for th in table.find("tr").find_all("th")]
        output_lines.append(f"Found headers: {headers}")
        
        # Extract table rows
        rows = []
        for row in table.find_all("tr")[1:]:
            row_data = []
            for cell in row.find_all("td"):
                cell_data = set([div.text.strip() for div in cell.find_all("div")])
                row_data.append(", ".join(cell_data) if cell_data else "")
            row_data = row_data[:len(headers)] + [""] * (len(headers) - len(row_data))
            rows.append(row_data)
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=headers)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for n in range(min(len(days), len(df))):
            df.at[n, "Day / Period"] = days[n]
        
        # Save CSV locally (optional)
        df.to_csv("scraped_table.csv", index=False)
        output_lines.append("Table scraped and saved to CSV.")
        
        # --- Google Sheets Update Section (from Updation.py) ---
        output_lines.append("Updating Google Sheet...")
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        # Adjust the path below to your service account credentials JSON file.
        creds = Credentials.from_service_account_file(
            r"C:\Users\YASHIKA\Downloads\timetable-initiative-454015-007cb73b96c4.json", 
            scopes=scope
        )
        client = gspread.authorize(creds)
        
        # Open the target spreadsheet by key (adjust the key accordingly).
        spreadsheet = client.open_by_key("1SJ3Gbmx4u0NudnV5iS8P2p2G_fTImaPp-FIU3ctaF2Y")
        worksheet = spreadsheet.get_worksheet(0)
        
        # Convert DataFrame to list of lists.
        data = df.values.tolist()
        # Append the data rows to the sheet.
        worksheet.append_rows(data, value_input_option="USER_ENTERED")
        output_lines.append("Google Sheet updated successfully.")
        
        time.sleep(5)
        driver.quit()
        output_lines.append("Driver closed.")
    except Exception as e:
        output_lines.append(f"Error: {str(e)}")
    
    return "\n".join(output_lines)

@app.route("/", methods=["GET", "POST"])
def index():
    output = None
    if request.method == "POST":
        # Running the process in a separate thread is one option,
        # but here we run synchronously and capture the output.
        output = run_process()
    return render_template_string(HTML_TEMPLATE, output=output)

if __name__ == "__main__":
    # Run the Flask app on port 5000. Adjust host and debug as needed.
    app.run(debug=True)
