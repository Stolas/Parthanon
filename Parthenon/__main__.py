#!/usr/bin/env python

import requests
from tqdm import tqdm
import json
import re
from datetime import datetime
import argparse

def add_card(jobj, set_=None):

# {"Retainer", "Imbued",     "Equipment",        "Reaction",        "Vampire", "Ally",     "Power",      "Political Action", "Action Modifier", "Action", "Event",    "Conviction", "Combat",           "Master"};
    capacity = 0
    group = 0
    pool_cost = 0
    blood_cost = 0

    name = jobj['_name']
    types = jobj['types']
    unique_id = jobj["id"]
    card_text = jobj['card_text']
    clans = jobj.get('clans', [])
    disciplines = jobj.get('disciplines', [])
    has_advanced = jobj.get('has_advanced', False)
    advanced = jobj.get('adv', False)
    burn = jobj.get('Burn Option', False)
    is_banned =  "banned" in jobj.keys()

    is_crypt = "Vampire" in types or "Imbued" in types
    is_minion = "Retainer" in types or "Ally" in types
    if is_crypt:
        capacity = jobj['capacity']
        group = jobj['group']
    else:
        pool_cost = jobj.get('pool_cost', 0)
        blood_cost = jobj.get('blood_cost', 0)

    try:
        scan_url = jobj["scans"][set_]
    except KeyError:
        scan_url = jobj["url"]
    modern_picture_url = jobj["url"]

    card = {}
    card['capacity'] = capacity
    card['group'] = group
    card['pool_cost'] = pool_cost
    card['blood_cost'] = blood_cost
    card['name'] = name
    card['types'] = types
    card['unique_id'] = unique_id
    card['card_text'] = card_text
    card['clans'] = clans
    card['disciplines'] = disciplines
    card['has_advanced'] = has_advanced
    card['advanced'] = advanced
    card['burn'] = burn
    card['banned'] = is_banned
    card['is_crypt'] = is_crypt
    card['is_minion'] = is_minion
    card['is_library'] = not is_crypt
    card['capacity'] = capacity
    card['group'] = group
    card['scan_url'] = scan_url
    card['url'] = modern_picture_url
    card['traits'] = {}
    card['traits']['crypt'] = None
    card['traits']['library'] = None
    card['traits']['minion'] = None

    # Note; Most regex stolen from vdb.im

    if is_crypt:
        card['traits']['crypt'] = {}
        trait_regexs = {}
        trait_regexs['infernal'] = "Infernal\."
        trait_regexs['black hand'] = "black hand\."
        trait_regexs['red list'] = "red -list\."
        trait_regexs['add_bleed'] = "\+\d bleed"
        trait_regexs['add_strength'] = "\+\d strength"
        trait_regexs['add_intercept'] = "\+\d intercept"
        for key in trait_regexs:
            value = True if re.search(trait_regexs[key], card_text) else False
            card['traits']['crypt'][key] = value
    elif is_minion:
        card['traits']['minion'] = {}
        for value_name in ["bleed", "strength", "life"]:
            try:
                value = re.search(f"(\d+) {value_name}", card_text).group(1)
            except AttributeError:
                value = 0
            card['traits']['minion'][value_name] = int(value)
    else: # Library
        card['traits']['library'] = {}
        trait_regexs = {}
        trait_regexs['intercept'] = "-[0-9]+ stealth(?! \(d\))(?! \w)(?! action)|\+[0-9]+ intercept|gets -([0-9]|x)+ stealth|stealth to 0"
        trait_regexs['stealth'] = "\+[0-9]+ stealth(?! \(d\))(?! \w)(?! action)|-[0-9]+ intercept"
        trait_regexs['bleed'] = "\+([0-9]+|X) bleed"
        trait_regexs['strength'] = "\+[0-9]+ strength"
        trait_regexs['embrace'] = "becomes a.*(\d[ -]|same.*)capacity"
        trait_regexs['bounce bleed'] = "change the target of the bleed|is now bleeding"
        trait_regexs['unlock'] = "(?!not )unlock(?! phase|ed)|wakes"
        trait_regexs['votes-title'] = "\+. vote|additional vote|represent the .* title"
        trait_regexs['reduce bleed'] = "reduce (a|the)(.*) bleed (amount)?|bleed amount is reduced"
        trait_regexs['aggravated'] = "(?:[^non-])aggravated"
        trait_regexs['prevent'] = "(?:[^un])prevent(?:[^able])"
        trait_regexs['bloat'] = "(move|add) .* blood (from the blood bank )?to .* in your uncontrolled region"
        for key in trait_regexs:
            value = True if re.search(trait_regexs[key], card_text) else False
            card['traits']['library'][key] = value

    return card

def get_tokens():
    tokens = {}

    tokens['Anarch'] = "http://test"
    tokens['Black Hand'] = ""
    tokens['Corruption'] = "http://test"
    tokens['Edge'] = "http://test"
    tokens['Liaison'] = "http://test"
    tokens['Quintessence'] = "http://test"

    return tokens


def generate_card_database(server = "https://api.krcg.org"):
    card_db = {}
    resp = requests.get(f"{server}/card_search")
    sets = resp.json()["set"]

    for set_ in sets:
        print(f"Loading: {set_} ({sets.index(set_)}/{len(sets)})")
        payload = {}
        payload['set'] = [set_]
        card_db[set_] = {}
        card_db[set_]['crypt'] = []
        card_db[set_]['library'] = []

        result = requests.post(f"{server}/card_search", json=payload)
        for card_name in tqdm(result.json()):
            card_name = card_name.replace("/","")
            encoded_name = requests.utils.quote(card_name,safe="")
            card_resp = requests.get(f"{server}/card/{encoded_name}")
            # print(f"{encoded_name} {card_resp}")
            jobj = card_resp.json()

            if set_ in jobj["sets"]:
                card = add_card(jobj, set_)
                card_type = 'crypt' if card['is_crypt'] else 'library'
                card_db[set_][card_type].append(card)

    card_db['tokens'] = get_tokens()

    return card_db

if __name__ == '__main__':
    # parser = argparse.ArgumentParser(prog='ProgramName', description='What the program does', epilog='Text at the bottom of help')

    start_time = datetime.now()

    database = generate_card_database()
    with open("golconda.json", "w") as fd:
        fd.write(json.dumps(database))

    end_time = datetime.now()
    delta = end_time - start_time
    total_seconds = delta.total_seconds()
    minutes = int(total_seconds / 60)
    seconds = total_seconds % 60

    print(f"Required Time: {minutes}:{seconds}")
