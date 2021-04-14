from flask import Flask
from flask import jsonify
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

app = Flask(__name__)

def scrape_champions(db: any):
    try:
        l = []
        opts = Options()
        opts.set_headless()
        assert opts.headless  # Operating in headless mode
        browser = Firefox(options=opts)
        champions_url = 'https://gol.gg/champion/list/season-S11/split-Spring/tournament-ALL/'

        browser.get(champions_url)

        champions_table = browser.find_element_by_class_name('playerslist')
        body_champions_table = champions_table.find_element_by_css_selector('tbody')
        champions_rows = body_champions_table.find_elements_by_css_selector('tr')

        for row in champions_rows:
             champion_name = row.find_elements_by_css_selector('td')[0].text
             champion_url = row.find_elements_by_css_selector('td')[0].find_element_by_css_selector('a').get_attribute('href')

             champions_ref = db.collection(u'champions')
             query_ref = champions_ref.where('name', '==', champion_name).stream()
             if sum(1 for _ in query_ref) == 0:
                doc_ref = db.collection(u'champions').document()
                doc_ref.set({
                    u'name': champion_name,
                    u'statsUrl': champion_url,
                    u'isAgainstUpdated': False
                })

        return "Champions loaded!"
    except Exception as e:
        return "An error has ocurred" + str(e)


def scrape_champions_picks(db):
    try:
        # roles = ['ALL', 'TOP', 'JUNGLE', 'MID', 'BOT', 'SUPPORT']
        roles = ['ALL']

        champions_ref = db.collection('champions').stream()

        for champion in champions_ref:
            champion_id = champion.id
            parsed_champion = champion.to_dict()
            champion_name = parsed_champion.get('name')
            print(champion_name)
            status_url = parsed_champion.get('statsUrl')
            isAgainstUpdated = parsed_champion.get('isAgainstUpdated')
            if not isAgainstUpdated:
                l = []
                opts = Options()
                opts.set_headless()
                assert opts.headless  # Operating in headless mode
                browser = Firefox(options=opts)
                browser.get(status_url)
                time.sleep(5)
                print('Refresh page for new champion')
                # ALL TOP JUNGLE MID BOT SUPPORT

                for role in roles:
                    # browser.find_element_by_xpath("//a[@role-value = role]"));
                    # browser.find_element_by_xpath("//select[@name='patch']/option[text()='11.2']").click()

                    # Set game version to 13
                    browser.find_element_by_xpath("//select[@name='patch']/option[text()='11.2']").click()
                    print('new version select')
                    time.sleep(4)

                    # Get strong against
                    strong_against_table = browser.find_element_by_xpath("//table[@class='table_list' and .//th[.='Strong Against']]")
                    body_strong_against_table = strong_against_table.find_element_by_css_selector('tbody')
                    strong_against_row = body_strong_against_table.find_elements_by_css_selector('tr')

                    strong_ref = db.collection(u'champions').document(champion_id).collection('strongAgainst').stream()
                    
                    for strongChampion in strong_ref:
                        strongChampion.reference.delete()
                    
                    for strong_champion in strong_against_row:
                        validation_text = strong_champion.find_elements_by_css_selector('td')[0].text
                        if (validation_text != '' and validation_text != ' ' and validation_text[-1] != '!'):
                            strong_name = strong_champion.find_elements_by_css_selector('td')[0].text.strip()
                            strong_percentage = strong_champion.find_elements_by_css_selector('td')[1].text.strip()
                            strong_ref = db.collection(u'champions').document(champion_id).collection('strongAgainst').document()
                            strong_ref.set({ 'name': strong_name, 'percentage': strong_percentage }, merge=True)

                    print('Strong against added')

                    # Get weak against
                    weak_against_table = browser.find_element_by_xpath("//table[@class='table_list' and .//th[.='Weak Against']]")
                    body_weak_against_table = weak_against_table.find_element_by_css_selector('tbody')
                    weak_against_row = body_weak_against_table.find_elements_by_css_selector('tr')

                    counter_ref = db.collection(u'champions').document(champion_id).collection('weakAgainst').stream()

                    for counterChampion in counter_ref:
                        counterChampion.reference.delete()

                    for counter in weak_against_row:
                        validation_text = counter.find_elements_by_css_selector('td')[0].text
                        print(validation_text)
                        if (validation_text != '' and validation_text != ' ' and validation_text[-1] != '!'):
                            counter_name = counter.find_elements_by_css_selector('td')[0].text.strip()
                            counter_percentage = counter.find_elements_by_css_selector('td')[1].text.strip()
                            counter_ref = db.collection(u'champions').document(champion_id).collection('weakAgainst').document()
                            counter_ref.set({ 'name': counter_name, 'percentage': counter_percentage }, merge=True)
                    print('Counters added')

                    updatedChamp_ref = db.collection(u'champions').document(champion_id)
                    updatedChamp_ref.set({ 'isAgainstUpdated': True }, merge=True)
                    browser.quit()
            else:
                print('Already Updated')
        return "Counter and options loaded!"
    except Exception as e:
        browser.quit()
        return "An error has ocurred " + str(e)

def reset_picks_status(db):
    try:
        champions_ref = db.collection('champions').stream()

        for champion in champions_ref:
            champion.reference.update({ 'isAgainstUpdated': False })

        return "Pick flags are reset"
    except Exception as e:
        return "An error has ocurred " + str(e)


@app.route('/')
def set_champions():
    cred = credentials.Certificate("./hidden-project-lol-dev-firebase-adminsdk-j5qkz-d32451ffbf.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    return jsonify(Result=scrape_champions(db))

@app.route('/scrape_champions_picks')
def set_champions_pick():
    cred = credentials.Certificate("./hidden-project-lol-dev-firebase-adminsdk-j5qkz-d32451ffbf.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    return jsonify(Result=scrape_champions_picks(db))

@app.route('/reset_picks_status')
def set_picks_status():
    cred = credentials.Certificate("./hidden-project-lol-dev-firebase-adminsdk-j5qkz-d32451ffbf.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    return jsonify(Result=reset_picks_status(db))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)