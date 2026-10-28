import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# ==============================================================================
# COOK COUNTY DATA CONFIGURATION
# ==============================================================================
def get_cook_county_votes():
    """
    Parses the server-rendered HTML table from the Cook County Clerk site.
    """
    # UPDATE THIS: Ensure this matches the live dashboard URL on election night
    url = "https://cookcountyclerkil.gov"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This searches for the text header corresponding to your district
        target_header = soup.find(lambda tag: tag.name in ['h5', 'h4', 'div'] and "State Senator, 24th District" in tag.text)
        
        if not target_header:
            print("Cook County: State Senate 24 header not found. Returning zeroed placeholders.")
            return {"Lewis": 0, "McAdams": 0, "PrecinctsReporting": 0, "TotalPrecincts": 18}
            
        # Locate the results data table following the header
        table = target_header.find_next('table')
        votes_dict = {"Lewis": 0, "McAdams": 0, "PrecinctsReporting": 0, "TotalPrecincts": 18}
        
        # Parse precinct progress text (e.g., "0 of 18 Precincts Reported")
        precinct_text = target_header.text
        if "Precincts Reported" in precinct_text:
            try:
                parts = precinct_text.split("of")
                votes_dict["PrecinctsReporting"] = int(parts[0].strip().split()[-1])
                votes_dict["TotalPrecincts"] = int(parts[1].strip().split()[0])
            except Exception:
                pass

        # Loop through data rows to grab candidate vote counts
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                candidate_name = cols[0].text.strip()
                vote_count = int(cols[1].text.strip().replace(',', ''))
                
                # UPDATE THIS: Match exact candidate string fragments on the live roster
                if "Lewis" in candidate_name:
                    votes_dict["Lewis"] = vote_count
                elif "McAdams" in candidate_name:
                    votes_dict["McAdams"] = vote_count
                    
        return votes_dict
        
    except Exception as e:
        print(f"Error scraping Cook County: {e}")
        return {"Lewis": 0, "McAdams": 0, "PrecinctsReporting": 0, "TotalPrecincts": 18}

# ==============================================================================
# DUPAGE COUNTY DATA CONFIGURATION
# ==============================================================================
def get_dupage_county_votes():
    """
    Queries the raw structured summary data payload directly from DuPage's Clarity ENR.
    """
    # UPDATE THIS: The ID '125941' is a placeholder from a past election. 
    # Swap out '125941' with the active election ID number generated on election night.
    election_id = "125941" 
    url = f"https://dupageresults.gov{election_id}/json/sum.json"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        votes_dict = {"Lewis": 0, "McAdams": 0, "PrecinctsReporting": 0, "TotalPrecincts": 0}
        
        # Iterate over structural race listings to find State Senate 24
        for contest in data.get('Contests', []):
            if "State Senator, 24th District" in contest.get('Name', ''):
                votes_dict["PrecinctsReporting"] = contest.get('PrecinctsReporting', 0)
                votes_dict["TotalPrecincts"] = contest.get('TotalPrecincts', 0)
                
                # Step through array to isolate explicit candidates
                for choice in contest.get('Choices', []):
                    candidate_name = choice.get('Name', '')
                    vote_count = choice.get('Votes', 0)
                    
                    # UPDATE THIS: Match exact candidate string fragments inside Clarity JSON
                    if "Lewis" in candidate_name:
                        votes_dict["Lewis"] = vote_count
                    elif "McAdams" in candidate_name:
                        votes_dict["McAdams"] = vote_count
                        
                return votes_dict
                
        return votes_dict
    except Exception as e:
        print(f"Error pulling DuPage JSON data: {e}")
        return {"Lewis": 0, "McAdams": 0, "PrecinctsReporting": 0, "TotalPrecincts": 0}

# ==============================================================================
# DATA AGGREGATION & ENGINE LOGIC
# ==============================================================================
def main():
    cook = get_cook_county_votes()
    dupage = get_dupage_county_votes()
    
    # Mathematical summation of both pipelines
    total_lewis = cook["Lewis"] + dupage["Lewis"]
    total_mcadams = cook["McAdams"] + dupage["McAdams"]
    total_votes = total_lewis + total_mcadams
    
    total_reporting = cook["PrecinctsReporting"] + dupage["PrecinctsReporting"]
    total_precincts = cook["TotalPrecincts"] + dupage["TotalPrecincts"]
    
    output = {
        "last_updated": datetime.now().isoformat(),
        "precincts_reporting": total_reporting,
        "total_precincts": total_precincts,
        "reporting_percentage": round((total_reporting / total_precincts * 100), 2) if total_precincts > 0 else 0,
        "candidates": [
            {
                "name": "Seth Lewis (REP)", 
                "votes": total_lewis, 
                "percentage": round((total_lewis / total_votes * 100), 2) if total_votes > 0 else 0
            },
            {
                "name": "Benjamin McAdams (DEM)", 
                "votes": total_mcadams, 
                "percentage": round((total_mcadams / total_votes * 100), 2) if total_votes > 0 else 0
            }
        ],
        "breakdown": {
            "cook_county": cook,
            "dupage_county": dupage
        }
    }
    
    # Serialize structure back down onto clean physical storage file
    os.makedirs('data', exist_ok=True)
    with open('data/results.json', 'w') as f:
        json.dump(output, f, indent=4)
    print("Visualizer database file 'data/results.json' successfully updated!")

if __name__ == "__main__":
    main()
