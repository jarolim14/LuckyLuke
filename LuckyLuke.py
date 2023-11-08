from time import sleep

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class OddsetScraper:
    def __init__(
        self,
        url="https://pc-annahmestelle.oddset.de/de/wettscheinvorbereitung#m/all/s-441/cc-121A/t-2782/261/1",
    ):
        self.url = url
        self.driver = self.initiate_driver()
        self.matches = None

    def initiate_driver(self):
        options = webdriver.FirefoxOptions()
        driver = webdriver.Firefox(options=options)
        driver.get(self.url)
        print("Driver initiated")
        return driver  # You forgot this line

    def click_reject_all(self):
        reject_all_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
        )
        reject_all_button.click()
        sleep(0.5)
        self.driver.find_element(By.CLASS_NAME, "btn-active").click()
        sleep(0.5)

    def get_teams(self):
        span_elements = self.driver.find_elements(By.CLASS_NAME, "ellipsis.longer")
        teams = [span_element.text for span_element in span_elements]
        return teams[::2], teams[1::2]

    def get_matches(self, home_teams, away_teams):
        """here we need to click on the +8 links and then get the odds for the results. We need to scroll down to the bottom of the page to find the +8 links. Then we need to scroll down to the bottom of the page again to find the odds. Then we safe the odds in a dictionary with the match as key and the odds as values."""
        self.matches = {}
        for index, (ht, at) in enumerate(zip(home_teams, away_teams)):
            sleep(1)

            # Find the "+8" links again, in case the page has changed
            more_bets_elements = self.driver.find_elements(
                By.XPATH, "//a[contains(text(), '+8')]"
            )
            if index >= len(more_bets_elements):
                print("No more matches")
                break
            more_bets_element = more_bets_elements[index]
            # print(f"Starting {ht} : {at}")
            self.driver.execute_script(
                "arguments[0].scrollIntoView();", more_bets_element
            )
            ActionChains(self.driver).move_to_element(
                more_bets_element
            ).click().perform()
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//h2[contains(text(), "Ergebniswette")]')
                )
            )
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//img[@src='/Oddset-theme/images/plusb.png']")
                )
            )
            sleep(1)
            plus_button = self.driver.find_element(
                By.XPATH, "//img[@src='/Oddset-theme/images/plusb.png']"
            )
            # scroll down
            self.driver.execute_script("arguments[0].scrollIntoView();", plus_button)

            # Wait for the element to be clickable
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//img[@src='/Oddset-theme/images/plusb.png']",
                    )
                )
            )
            # Re-find the element
            plus_button = self.driver.find_element(
                By.XPATH, "//img[@src='/Oddset-theme/images/plusb.png']"
            )
            plus_button.click()
            # Wait for the element to be clickable
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//h2[contains(text(), 'Ergebniswette')]/following-sibling::*",
                    )
                )
            )
            elements = self.driver.find_elements(
                By.XPATH, "//h2[contains(text(), 'Ergebniswette')]/following-sibling::*"
            )
            res_and_odd = elements[0].text.split("\n")[1:]
            results = res_and_odd[::2]
            odds = res_and_odd[1::2]
            r_o_df = pd.DataFrame(
                {"result": results, "odds": [float(o.replace(",", ".")) for o in odds]}
            )
            r_o_df.sort_values(
                by="odds", ascending=True, inplace=True, ignore_index=True
            )
            self.matches[ht + " : " + at] = r_o_df
            print(f"Finished {ht} : {at}")
            sleep(1)
            self.driver.back()
        self.driver.quit()
        return self.matches

    def final_predictions(self):
        self.final_predictions_dict = {}
        for key, df in self.matches.items():
            lowest_odd = df.loc[0, "odds"]
            lowest_result = df.loc[0, "result"]
            second_odd = df.loc[1, "odds"]
            second_result = df.loc[1, "result"]
            # print(lowest_odd, second_odd)
            # if lowest result is 1:1, check whether second result within .5 difference in odds. If yes, take second result
            if lowest_result == "1:1":
                if abs(lowest_odd - second_odd) < 1.3:
                    self.final_predictions_dict[key] = second_result
                else:
                    self.final_predictions_dict[key] = lowest_result
            else:
                self.final_predictions_dict[key] = lowest_result
        return self.final_predictions_dict

    def run(self):
        self.click_reject_all()
        home_teams, away_teams = self.get_teams()
        self.get_matches(home_teams, away_teams)
        return self.final_predictions()


class TeamtipPlacer:
    def __init__(self, final_predictions_dict):
        self.url = "https://teamtip.net/dashboard"
        self.email = "raft_razz.0x@icloud.com"
        self.password = "pewhik-qoxgi2-jaqsoJ"
        self.driver = self.initiate_driver()
        self.final_predictions_dict = final_predictions_dict

    def initiate_driver(self):
        options = webdriver.FirefoxOptions()
        driver = webdriver.Firefox(options=options)
        driver.get(self.url)
        print("Driver initiated")
        return driver

    def login(self):
        # Wait and click login
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/login']"))
        ).click()

        # Wait and enter email
        email_input = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "email"))
        )
        email_input.send_keys(self.email)

        # Wait and enter password
        password_input = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "password"))
        )
        password_input.send_keys(self.password)

        # Wait and click login button
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        ).click()

    def view_bets(self):
        # view bets
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "view_bets_button"))
        ).click()
        # Wait and find bet inputs
        bet_input_home = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "bet_input_home"))
        )
        bet_input_guest = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "bet_input_guest"))
        )
        # wait and find team names
        match_teamname = [
            team.text
            for team in WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "match-teamname"))
            )
        ]
        home_teams = match_teamname[::2]
        away_teams = match_teamname[1::2]
        return home_teams, away_teams, bet_input_home, bet_input_guest

    def place_bets(self, home_teams, away_teams, bet_input_home, bet_input_guest):
        for i, (home_team, away_team) in enumerate(zip(home_teams, away_teams)):
            # Create a tuple of the current home and away team to search for in the predictions
            current_match = (home_team, away_team)

            # Find the match in the predictions dictionary where both teams are present
            match_found = False
            for match, prediction in self.final_predictions_dict.items():
                if home_team in match or away_team in match:
                    match_found = True
                    bet_input_home[i].click()
                    bet_input_home[i].send_keys(prediction.split(":")[0])
                    bet_input_guest[i].click()
                    bet_input_guest[i].send_keys(prediction.split(":")[1])
                    # print the match and the prediction and the teams
                    print(match, prediction, home_team, away_team)
                    break

            if not match_found:
                print("ALARM: No match found for", home_team, away_team)
                # Handle the case where no match is found, e.g., skip or log an error

        sleep(2)
        # Go to the previous page
        self.driver.back()
        sleep(2)
        self.driver.quit()

    def run(self):
        self.login()
        home_teams, away_teams, bet_input_home, bet_input_guest = self.view_bets()
        self.place_bets(home_teams, away_teams, bet_input_home, bet_input_guest)


if __name__ == "__main__":
    oddsetscraper = OddsetScraper()
    final_predictions_dict = oddsetscraper.run()
    # print(final_predictions_dict)
    ttp = TeamtipPlacer(final_predictions_dict)
    ttp.run()
    print("This was great! Lets win this!")
