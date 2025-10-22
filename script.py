import base64
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd 

def get_energy_data():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except:
        pass
    
    all_data = []
    
    # loading page and selecting themes, years and countries
    try:
        driver.get("https://africa-energy-portal.org/database")
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".filter-item-field"))
        )

        theme = driver.find_element(By.CSS_SELECTOR, "input.select-all-themes")
        driver.execute_script("arguments[0].click();", theme)
        time.sleep(2)
        
        year_dropdown = driver.find_element(By.CSS_SELECTOR, ".year-dropdown-field .custom-dropdown-label")
        driver.execute_script("arguments[0].click();", year_dropdown)

        year_checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".year-dropdown-field input.custom-dropdown-select-all"))
        )
        driver.execute_script("arguments[0].click();", year_checkbox)
        time.sleep(2)

        #clear logs       
        _ = driver.get_log("performance")
                
        country_dropdown = driver.find_element(By.CSS_SELECTOR, ".country-dropdown-field .custom-dropdown-label")
        driver.execute_script("arguments[0].click();", country_dropdown)
        
        country_checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".country-dropdown-field input.custom-dropdown-select-all"))
        )
        driver.execute_script("arguments[0].click();", country_checkbox)
        time.sleep(5)
        
        # Extract JSON data from network responses
        logs = driver.get_log("performance")
        for log_entry in logs:
            try:
                message = json.loads(log_entry["message"])["message"]
                if message["method"] == "Network.responseReceived":
                    url = message["params"]["response"]["url"]
                    if any(keyword in url for keyword in ["views/ajax", "/database", "/get-database-data", "/api"]):
                        request_id = message["params"]["requestId"]
                        result = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                        body = result["body"]
                        if result.get("base64Encoded"):
                            body = base64.b64decode(body).decode("utf-8")
                        data = json.loads(body)
                        all_data.append(data)
            except:
                continue
        
        # save clean data
        with open("energy_data_clean.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2)
        
        print(f"Saved {len(all_data)} data items to energy_data_clean.json")
        
    finally:
        driver.quit()
    
    return all_data

if __name__ == "__main__":
    data = get_energy_data()
    print(f"Retrieved {len(data)} data responses")
    index_columns = ['name', 'id','indicator_group','indicator_topic', 'indicator_name','unit', 'url']
    
    df = pd.json_normalize(data[0], "data").pivot(
        index=index_columns, 
        columns='year', 
        values='score'
    ).reset_index()
    
    df.to_csv('energy_data.csv', index=False)
    print(f"CSV saved with {len(df)} rows")